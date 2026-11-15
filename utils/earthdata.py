"""
earthdata.py — Humedad del suelo SMAP y lluvia GPM SATELITALES para cualquier punto del planeta.

  SMAP L4 (SPL4SMGP v8, NSIDC), celdas de 9 km
      sm_surface  humedad superficial 0–5 cm (m³/m³)   → PROMEDIO mensual → smap_moisture
      sm_rootzone humedad de la zona de raíces (m³/m³)  → PROMEDIO mensual → humedad_raiz
  GPM IMERG Final mensual (GPM_3IMERGM v07, GES DISC), celdas de 0.1° (~11 km)
      precipitation (mm/h) × horas del mes                                → precipitation

No descarga archivos completos: usa OPeNDAP, así el servidor de la NASA recorta y envía
solo los píxeles del punto (pocos KB por fecha). Necesita:
  - pip install earthaccess
  - Variable de entorno EARTHDATA_TOKEN con un token de https://urs.earthdata.nasa.gov
    (y la app "NASA GESDISC DATA ARCHIVE" autorizada en el perfil de Earthdata).

El NDVI de MODIS que ya tenga el CSV se conserva.
"""
import calendar
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import numpy as np
import pandas as pd

from config import ESTRES
from utils.datos import COLUMNAS, RAIZ, cargar_meta, ruta_meta
from utils.nasa_power import FUENTE_NDVI

INICIO = date(ESTRES["anio_inicio"], 4, 1)   # abril de 2015: inicio de los datos científicos de SMAP
CACHE = RAIZ / "data" / ".cache"
DIAS_CACHE_LISTAS = 7                        # la lista de archivos de la NASA se renueva cada semana
HILOS, REINTENTOS = 8, 4
PASO_SMAP_DIAS = 5                           # 1 muestra de SMAP cada 5 días (≈ 3 min por punto)

SMAP_SHORT, SMAP_HORA = "SPL4SMGP", "T133000"
SMAP_FILAS, SMAP_COLS = 1624, 3856           # malla EASE-Grid 2.0 global de 9 km
GPM_SHORT = "GPM_3IMERGM"

FUENTE_HUMEDAD = "SMAP L4 (SPL4SMGP v8, 9 km)"
FUENTE_LLUVIA = "GPM IMERG Final (GPM_3IMERGM v07, 0.1°)"


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------
def _cargar_token():
    """Lee EARTHDATA_TOKEN. En Windows también lo busca en las variables del usuario
    (por si la terminal se abrió antes de crearlo)."""
    if os.environ.get("EARTHDATA_TOKEN"):
        return True
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                os.environ["EARTHDATA_TOKEN"] = winreg.QueryValueEx(k, "EARTHDATA_TOKEN")[0]
                return True
        except OSError:
            pass
    return False


def falta_para_descargar():
    """None si se puede descargar; si no, un mensaje corto que explica qué falta."""
    try:
        import earthaccess  # noqa: F401
    except ImportError:
        return "Falta instalar earthaccess: py -m pip install earthaccess"
    if not _cargar_token():
        return "Falta la variable EARTHDATA_TOKEN (token gratis en urs.earthdata.nasa.gov)."
    return None


def _sesion():
    import earthaccess
    if not _cargar_token():
        raise RuntimeError("Falta la variable EARTHDATA_TOKEN.")
    auth = earthaccess.login(strategy="environment")
    if not (auth and auth.authenticated):
        raise RuntimeError("Earthdata rechazó el token: genere uno nuevo en urs.earthdata.nasa.gov.")
    return earthaccess, earthaccess.get_requests_https_session()


def _pedir(sesion, url, params=None):
    for intento in range(REINTENTOS):
        try:
            r = sesion.get(url, params=params, timeout=180)
            if r.status_code == 200:
                return r.text
            if r.status_code in (401, 403):
                raise RuntimeError(f"Acceso denegado ({r.status_code}). Revise el token de Earthdata.")
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(2 ** intento)
    raise RuntimeError(f"No se pudo descargar: {url}")


def _leer_texto_opendap(texto):
    """Respuesta de texto de OPeNDAP (.dap.csv) → {variable: matriz}. Cada línea 'var[i], v1, v2…' es una fila."""
    datos = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("Dataset:") or "," not in linea:
            continue
        cabeza, *valores = [x.strip() for x in linea.split(",")]
        nombre = cabeza.split("[")[0].split("/")[-1]
        try:
            datos.setdefault(nombre, []).append([float(v) for v in valores if v])
        except ValueError:
            continue
    return {k: np.array(v) for k, v in datos.items()}


def _en_paralelo(funcion, tareas, etapa, al_avanzar):
    resultados = []
    with ThreadPoolExecutor(HILOS) as ex:
        for n, res in enumerate(ex.map(funcion, tareas), 1):
            resultados.append(res)
            if al_avanzar:
                al_avanzar(etapa, n, len(tareas))
    return resultados


def _lista_granulos(earthaccess, clave, consulta, fecha_de_nombre):
    """[(fecha, url_opendap)]. Buscar en el catálogo tarda ~1 min y la lista sirve para
    cualquier punto, así que se guarda en data/.cache/ por unos días."""
    ruta = CACHE / f"granulos_{clave}.json"
    if ruta.exists() and time.time() - ruta.stat().st_mtime < DIAS_CACHE_LISTAS * 86400:
        return [(datetime.fromisoformat(f).date(), u) for f, u in json.loads(ruta.read_text(encoding="utf-8"))]
    lista = []
    for g in earthaccess.search_data(**consulta):
        fecha = fecha_de_nombre(g["umm"]["GranuleUR"])
        link = next((u["URL"] for u in g["umm"].get("RelatedUrls", [])
                     if "opendap" in u.get("URL", "").lower()), None)
        if fecha and link:
            lista.append((fecha, link))
    if lista:
        CACHE.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps([(f.isoformat(), u) for f, u in lista]), encoding="utf-8")
    return lista


# ---------------------------------------------------------------------------
# SMAP L4
# ---------------------------------------------------------------------------
def _ease2_fila_col(lat, lon):
    """Fila/columna aproximada en la malla EASE-Grid 2.0 global de 9 km (EPSG:6933)."""
    a, e, celda = 6378137.0, 0.0818191908426215, 9008.055210146
    s1 = math.sin(math.radians(30.0))
    k0 = math.cos(math.radians(30.0)) / math.sqrt(1 - e * e * s1 * s1)
    s = math.sin(math.radians(lat))
    q = (1 - e * e) * (s / (1 - e * e * s * s) - (1 / (2 * e)) * math.log((1 - e * s) / (1 + e * s)))
    fila = int((SMAP_FILAS / 2 * celda - a * q / (2 * k0)) // celda)
    col = int((a * k0 * math.radians(lon) + SMAP_COLS / 2 * celda) // celda)
    return fila, col


def _smap(earthaccess, sesion, lat, lon, fin, al_avanzar):
    urls = dict(_lista_granulos(
        earthaccess, f"smap_{INICIO:%Y%m}_{fin:%Y%m}",
        dict(short_name=SMAP_SHORT, temporal=(INICIO.isoformat(), f"{fin.isoformat()}T23:59:59"),
             granule_name=f"*{SMAP_HORA}*", count=-1),
        lambda n: datetime.strptime(n.split("_")[4][:8], "%Y%m%d").date() if SMAP_HORA in n else None))
    urls = {d: u for d, u in urls.items() if (d - INICIO).days % PASO_SMAP_DIAS == 0}
    if not urls:
        raise RuntimeError("SMAP: no se encontraron archivos.")

    # Celda más cercana: fila/columna aproximada por fórmula y luego se busca alrededor
    f_aprox, c_aprox = _ease2_fila_col(lat, lon)
    a0, b0 = max(f_aprox - 3, 0), max(c_aprox - 3, 0)
    a1, b1 = min(f_aprox + 3, SMAP_FILAS - 1), min(c_aprox + 3, SMAP_COLS - 1)
    ejemplo = next(iter(urls.values()))
    caja = _leer_texto_opendap(_pedir(sesion, ejemplo + ".dap.csv", {
        "dap4.ce": f"/cell_lat[{a0}:1:{a1}][{b0}:1:{b1}];/cell_lon[{a0}:1:{a1}][{b0}:1:{b1}]"}))
    dist = (caja["cell_lat"] - lat) ** 2 + (caja["cell_lon"] - lon) ** 2
    fi, ci = np.unravel_index(int(np.argmin(dist)), dist.shape)
    fila, col = a0 + int(fi), b0 + int(ci)
    pixel = {"lat": round(float(caja["cell_lat"][fi, ci]), 4), "lon": round(float(caja["cell_lon"][fi, ci]), 4)}
    # Se piden 2 columnas: OPeNDAP devuelve filas vacías si la última dimensión mide 1
    ce = (f"/Geophysical_Data/sm_surface[{fila}:1:{fila}][{col}:1:{col + 1}];"
          f"/Geophysical_Data/sm_rootzone[{fila}:1:{fila}][{col}:1:{col + 1}]")

    def una_fecha(item):
        dia, url = item
        try:
            d = _leer_texto_opendap(_pedir(sesion, url + ".dap.csv", {"dap4.ce": ce}))
            sup, raiz = d["sm_surface"][0, 0], d["sm_rootzone"][0, 0]
        except Exception:
            sup = raiz = -1.0                    # dato faltante; no detiene la descarga
        return {"date": pd.Timestamp(dia).to_period("M").to_timestamp(),
                "smap_moisture": np.nan if sup < 0 else sup, "humedad_raiz": np.nan if raiz < 0 else raiz}

    df = pd.DataFrame(_en_paralelo(una_fecha, sorted(urls.items()), "SMAP", al_avanzar))
    mensual = df.groupby("date").agg(smap_moisture=("smap_moisture", "mean"),
                                     humedad_raiz=("humedad_raiz", "mean"), dias=("smap_moisture", "count"))
    mensual.loc[mensual["dias"] < 3, ["smap_moisture", "humedad_raiz"]] = np.nan
    return mensual.drop(columns="dias"), pixel


# ---------------------------------------------------------------------------
# GPM IMERG
# ---------------------------------------------------------------------------
def _gpm(earthaccess, sesion, lat, lon, fin, al_avanzar):
    i, j = round((lon + 179.95) / 0.1), round((lat + 89.95) / 0.1)
    ce = f"/Grid/precipitation[0:1:0][{i}:1:{i}][{j}:1:{j + 1}]"   # 2 columnas (ver SMAP)
    lista = _lista_granulos(
        earthaccess, f"gpm_{INICIO:%Y%m}_{fin:%Y%m}",
        dict(short_name=GPM_SHORT, version="07", count=-1,
             temporal=(INICIO.isoformat(), f"{fin.isoformat()}T23:59:59")),
        lambda n: datetime.strptime(n.split("3IMERG.")[1][:8], "%Y%m%d").date() if "3IMERG." in n else None)
    if not lista:
        raise RuntimeError("GPM: no se encontraron archivos.")

    def un_mes(item):
        f, url = item
        m = pd.Timestamp(f)
        try:
            v = _leer_texto_opendap(_pedir(sesion, url + ".dap.csv", {"dap4.ce": ce}))["precipitation"][0, 0]
        except Exception:
            v = -1.0
        return {"date": m, "precipitation": np.nan if v < 0 else v * calendar.monthrange(m.year, m.month)[1] * 24}

    df = pd.DataFrame(_en_paralelo(un_mes, sorted(lista), "GPM", al_avanzar)).set_index("date")
    return df, {"lat": round(-89.95 + j * 0.1, 2), "lon": round(-179.95 + i * 0.1, 2)}


# ---------------------------------------------------------------------------
# Punto de entrada para la app
# ---------------------------------------------------------------------------
def descargar_smap_gpm(lat, lon, ruta_csv, al_avanzar=None):
    """Reemplaza humedad y lluvia del CSV por SMAP y GPM satelitales (conserva el NDVI de MODIS).
    al_avanzar(etapa, hechos, total) se llama mientras avanza. Devuelve el número de meses."""
    earthaccess, sesion = _sesion()
    fin = date.today()
    smap, pixel_smap = _smap(earthaccess, sesion, lat, lon, fin, al_avanzar)
    gpm, pixel_gpm = _gpm(earthaccess, sesion, lat, lon, fin, al_avanzar)

    tabla = smap.join(gpm, how="inner").dropna(subset=["smap_moisture", "precipitation"])
    if tabla.empty:
        raise RuntimeError("La NASA no tiene datos SMAP/GPM para este lugar (¿es agua?).")

    meta_anterior = cargar_meta(ruta_csv)
    existente = RAIZ / ruta_csv
    ndvi_real = meta_anterior.get("ndvi") == FUENTE_NDVI   # no el texto "datos de ejemplo" de una zona nueva
    if existente.exists() and ndvi_real:
        ndvi = pd.read_csv(existente, parse_dates=["date"]).set_index("date")["ndvi"]
        tabla["ndvi"] = ndvi.reindex(tabla.index)
    else:
        tabla["ndvi"] = np.nan

    tabla.index.name = "date"
    tabla = tabla.reset_index()
    tabla["date"] = tabla["date"].dt.strftime("%Y-%m-%d")
    tabla = tabla.round({"smap_moisture": 3, "humedad_raiz": 3, "precipitation": 1, "ndvi": 4})
    existente.parent.mkdir(parents=True, exist_ok=True)
    tabla[COLUMNAS + ["humedad_raiz"]].to_csv(existente, index=False)

    meta = {k: v for k, v in meta_anterior.items() if k.startswith("ndvi") and ndvi_real}
    meta.setdefault("ndvi", None)
    meta.update({
        "real": True,
        "descargado": date.today().isoformat(),
        "punto": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "humedad": FUENTE_HUMEDAD,
        "humedad_unidad": "m³/m³",
        "lluvia": FUENTE_LLUVIA,
        "nota": (f"Humedad del satélite SMAP (1 muestra cada {PASO_SMAP_DIAS} días, promedio mensual) y lluvia "
                 "del satélite GPM, vía NASA Earthdata (OPeNDAP). GPM Final se publica con meses de retraso."),
        "pixel_smap": pixel_smap,
        "pixel_gpm": pixel_gpm,
    })
    if meta.get("ndvi"):
        meta["ndvi_meses"] = int(tabla["ndvi"].notna().sum())
    ruta_meta(ruta_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(tabla)

"""
nasa_power.py — Descarga de DATOS REALES de la NASA para cualquier punto del planeta.

  NASA POWER (rápido, sin cuenta):
    PRECTOTCORR  lluvia diaria (mm/día)               → SUMA mensual     → precipitation
    GWETTOP      humedad del suelo superficial (0–1)  → PROMEDIO mensual → smap_moisture
    GWETROOT     humedad en la zona de raíces (0–1)   → PROMEDIO mensual → humedad_raiz
  MODIS MOD13Q1 vía ORNL DAAC (lento, sin cuenta):  ver utils/modis.py
    NDVI 250 m, máximo mensual → ndvi

⚠️ La humedad de NASA POWER viene del modelo MERRA-2 de la NASA, no del satélite SMAP.
"""
import json
import urllib.request
from datetime import date, timedelta

import pandas as pd

from config import ESTRES
from utils.datos import COLUMNAS, RAIZ, cargar_meta, ruta_meta
from utils.modis import descargar_ndvi_mensual

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETROS = ["PRECTOTCORR", "GWETTOP", "GWETROOT"]
INICIO = date(ESTRES["anio_inicio"], 4, 1)  # abril de 2015, igual que la misión SMAP
FUENTE_NDVI = "MODIS MOD13Q1 NDVI 250 m (ORNL DAAC)"


def _ayer():
    return date.today() - timedelta(days=1)


def url_power(lat, lon, inicio=INICIO, fin=None):
    fin = fin or _ayer()
    return (f"{API}?parameters={','.join(PARAMETROS)}&community=AG"
            f"&latitude={lat:.4f}&longitude={lon:.4f}"
            f"&start={inicio:%Y%m%d}&end={fin:%Y%m%d}&format=JSON")


def _json(url, tiempo_max=90):
    with urllib.request.urlopen(url, timeout=tiempo_max) as respuesta:
        return json.load(respuesta)


def a_mensual(datos_json):
    """Respuesta diaria de NASA POWER → tabla mensual (solo meses completos)."""
    p = datos_json["properties"]["parameter"]
    diario = pd.DataFrame({nombre: pd.Series(p[nombre]) for nombre in PARAMETROS})
    diario.index = pd.to_datetime(diario.index, format="%Y%m%d")
    diario = diario.where(diario != -999)

    grupos = diario.resample("MS")
    dias_validos = grupos["PRECTOTCORR"].count()
    mensual = pd.DataFrame({
        "precipitation": grupos["PRECTOTCORR"].sum(min_count=1),
        "smap_moisture": grupos["GWETTOP"].mean(),
        "humedad_raiz": grupos["GWETROOT"].mean(),
    })
    return mensual[dias_validos >= mensual.index.days_in_month]


def _leer_existente(ruta_csv):
    ruta = RAIZ / ruta_csv
    if not ruta.exists():
        return None
    df = pd.read_csv(ruta, parse_dates=["date"]).set_index("date")
    return df


def _guardar(ruta_csv, tabla, meta):
    tabla = tabla.copy()
    tabla.index.name = "date"
    tabla = tabla.reset_index()
    tabla["date"] = pd.to_datetime(tabla["date"]).dt.strftime("%Y-%m-%d")
    columnas = COLUMNAS + (["humedad_raiz"] if "humedad_raiz" in tabla else [])
    tabla = tabla.round({"precipitation": 1, "smap_moisture": 3, "humedad_raiz": 3, "ndvi": 4})[columnas]
    (RAIZ / ruta_csv).parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(RAIZ / ruta_csv, index=False)
    ruta_meta(ruta_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def descargar_power(lat, lon, ruta_csv):
    """Lluvia y humedad reales. Si el CSV ya tenía NDVI real de MODIS, se conserva."""
    url = url_power(lat, lon)
    datos = _json(url)
    mensual = a_mensual(datos)
    if mensual.empty:
        raise ValueError("NASA POWER respondió sin meses completos para este punto.")

    meta_anterior = cargar_meta(ruta_csv)
    existente = _leer_existente(ruta_csv)
    if meta_anterior.get("ndvi") == FUENTE_NDVI and existente is not None and "ndvi" in existente:
        mensual["ndvi"] = existente["ndvi"].reindex(mensual.index)
    else:
        mensual["ndvi"] = float("nan")

    elevacion = (datos.get("geometry") or {}).get("coordinates", [None, None, None])[2]
    meta = {
        **{k: v for k, v in meta_anterior.items() if k.startswith("ndvi")},
        "real": True,
        "descargado": date.today().isoformat(),
        "punto": {"lat": round(lat, 4), "lon": round(lon, 4), "elevacion_m": elevacion},
        "humedad": "NASA POWER GWETTOP (modelo MERRA-2)",
        "humedad_unidad": "fracción 0–1",
        "lluvia": "NASA POWER PRECTOTCORR",
        "url_power": url,
    }
    meta.setdefault("ndvi", None)
    _guardar(ruta_csv, mensual, meta)
    return len(mensual)


def descargar_ndvi(lat, lon, ruta_csv, al_avanzar=None):
    """NDVI satelital real de MODIS (tarda varios minutos). Requiere haber bajado NASA POWER antes."""
    existente = _leer_existente(ruta_csv)
    meta = cargar_meta(ruta_csv)
    if existente is None or not meta.get("real"):
        descargar_power(lat, lon, ruta_csv)
        existente, meta = _leer_existente(ruta_csv), cargar_meta(ruta_csv)

    ndvi = descargar_ndvi_mensual(lat, lon, INICIO, _ayer(), al_avanzar)
    if ndvi.empty:
        raise ValueError("MODIS no devolvió imágenes para este punto.")
    existente["ndvi"] = ndvi.reindex(existente.index)
    meta.update({"ndvi": FUENTE_NDVI, "ndvi_descargado": date.today().isoformat(),
                 "ndvi_meses": int(existente["ndvi"].notna().sum())})
    _guardar(ruta_csv, existente, meta)
    return meta["ndvi_meses"]

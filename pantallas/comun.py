"""
comun.py — Estado compartido, navegación, parcelas (demo + cualquier punto del mundo),
descarga de datos reales y cálculos que usan varias pantallas.
"""
import re

import streamlit as st

from config import MESES, PARCELA_INICIAL, PARCELAS, PERFIL_INICIAL, ROTACIONES
from utils.calendario import generar_calendario
from utils.datos import cargar_meta, cargar_serie, fecha_modificacion
from utils.estres import calcular_ventana_estres
from utils.geo import cargar_parcelas, centroide
from utils.nasa_power import descargar_ndvi, descargar_power
from utils.semaforo import calcular_semaforo

PASOS = ["Inicio", "1  Parcela", "2  Suelo", "3  Ventana de estrés", "4  Rotaciones", "5  Calendario", "6  Informe"]
INICIO, PARCELA, SUELO, VENTANA, ROTACIONES_PASO, CALENDARIO, INFORME = range(7)


def iniciar_estado():
    ss = st.session_state
    if ss.get("paso") is None:  # clic otra vez en el paso activo deja el control vacío
        ss.paso = ss.get("_ultimo_paso", PASOS[INICIO])
    ss._ultimo_paso = ss.paso
    ss.setdefault("parcela", PARCELA_INICIAL)
    ss.setdefault("perfil", dict(PERFIL_INICIAL))
    ss.setdefault("intentos_descarga", {})
    ss.setdefault("puntos", {})
    if ss.paso != PASOS[SUELO]:  # campos del paso 2 se rellenan desde el perfil al volver
        for clave in [k for k in ss.keys() if str(k).startswith("w_")]:
            del ss[clave]


# ---------------- Navegación ----------------
def ir_a(indice):
    st.session_state.paso = PASOS[indice]


def boton_siguiente(indice, texto, clave=None):
    st.button(texto, type="primary", on_click=ir_a, args=(indice,), key=clave)


def boton_ir(indice, texto, clave=None):
    st.button(texto, on_click=ir_a, args=(indice,), key=clave)


# ---------------- Parcelas: demostración + puntos elegidos en el mapa ----------------
@st.cache_data(show_spinner=False)
def _poligonos_demo():
    return cargar_parcelas()


def parcelas():
    demo = _poligonos_demo()
    todas = {pid: {**info, "feature": demo[pid], "demo": True} for pid, info in PARCELAS.items()}
    todas.update(st.session_state.get("puntos", {}))
    return todas


def parcela(pid=None):
    return parcelas()[pid or st.session_state.parcela]


def crear_zona(geometria, nombre, numero):
    """
    Arma una parcela nueva a partir de lo que el técnico dibujó en el mapa:
      - Polygon (polígono o rectángulo): se usa tal cual.
      - Point (marcador): se crea un cuadrado de ≈ 1.5 ha alrededor.
    Funciona en cualquier lugar del mundo: los datos se piden para el centro de la zona.
    """
    if geometria["type"] == "Point":
        lon, lat = geometria["coordinates"][:2]
        d = 0.00055  # ≈ 61 m → cuadrado de ≈ 1.5 ha
        geometria = {"type": "Polygon", "coordinates": [[
            [lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]}
    feature = {"type": "Feature", "properties": {}, "geometry": geometria}
    lat, lon = centroide(feature)
    pid = f"zona_{lat:.4f}_{lon:.4f}".replace("-", "m").replace(".", "_")
    feature["properties"]["id"] = pid
    return pid, {"nombre": nombre or f"Zona dibujada {numero}", "lugar": f"Lat {lat:.4f}, Lon {lon:.4f}",
                 "csv": f"data/puntos/{pid}.csv", "semilla_mock": 3, "feature": feature, "demo": False}


def agregar_zona(geometria, nombre=None):
    pid, info = crear_zona(geometria, nombre, len(st.session_state.puntos) + 1)
    st.session_state.puntos[pid] = info
    st.session_state.parcela = pid
    return pid


def coordenadas(pid=None):
    return centroide(parcela(pid)["feature"])


# ---------------- Datos reales de la NASA ----------------
def asegurar_datos_reales(pid):
    """Primera vez que se abre una parcela: descarga NASA POWER (rápido). Sin internet, sigue con ejemplo."""
    info, intentos = parcela(pid), st.session_state.intentos_descarga
    if cargar_meta(info["csv"])["real"] or pid in intentos:
        return
    with st.spinner("Descargando lluvia y humedad del suelo de NASA POWER…"):
        intentos[pid] = _intentar(lambda: descargar_power(*coordenadas(pid), info["csv"]), "meses de NASA POWER")


def actualizar_power(pid):
    st.session_state.intentos_descarga[pid] = _intentar(
        lambda: descargar_power(*coordenadas(pid), parcela(pid)["csv"]), "meses de NASA POWER")


def actualizar_ndvi(pid, barra):
    """NDVI de MODIS: lento (varios minutos). Muestra una barra de progreso."""
    al_avanzar = lambda hechos, total: barra.progress(hechos / total, text=f"Imágenes MODIS: {hechos} de {total} consultas")
    resultado = _intentar(lambda: descargar_ndvi(*coordenadas(pid), parcela(pid)["csv"], al_avanzar), "meses de NDVI MODIS")
    st.session_state.intentos_descarga[f"ndvi_{pid}"] = resultado
    return resultado


def _intentar(funcion, unidad):
    try:
        return {"ok": True, "mensaje": f"Listo: {funcion()} {unidad}."}
    except Exception as error:  # sin internet, servicio caído, etc.
        print(f"[ChakraSat] Descarga fallida: {error}")
        return {"ok": False, "mensaje": "No se pudo conectar con el servicio de la NASA (sin internet o servicio "
                                        "no disponible). La app sigue con los datos que ya tiene."}


def error_descarga(pid):
    intento = st.session_state.intentos_descarga.get(pid)
    return intento["mensaje"] if intento and not intento["ok"] else None


# ---------------- Datos con caché (se renueva cuando cambia el CSV) ----------------
@st.cache_data(show_spinner=False)
def _serie(csv, semilla, _version):
    return cargar_serie(csv, semilla)


@st.cache_data(show_spinner=False)
def _estres(csv, semilla, _version):
    return calcular_ventana_estres(_serie(csv, semilla, _version))


def serie_parcela(pid=None):
    info = parcela(pid)
    return _serie(info["csv"], info["semilla_mock"], fecha_modificacion(info["csv"]))


def estres_parcela(pid=None):
    info = parcela(pid)
    return _estres(info["csv"], info["semilla_mock"], fecha_modificacion(info["csv"]))


def meta_parcela(pid=None):
    return cargar_meta(parcela(pid)["csv"])


def analizar_rotaciones(perfil, pid=None):
    estres = estres_parcela(pid)
    resultados = {}
    for clave, rotacion in ROTACIONES.items():
        cal = generar_calendario(rotacion, estres)
        resultados[clave] = {"rotacion": rotacion, "calendario": cal,
                             "semaforo": calcular_semaforo(rotacion, cal, perfil)}
    mejor = max(resultados, key=lambda k: resultados[k]["semaforo"]["puntaje"])
    return resultados, mejor


# ---------------- Textos ----------------
def markdown_a_html(texto):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)


def rango_meses(meses):
    """[9, 10] → 'Sep–Oct' si son seguidos; si no, 'Sep, Nov'."""
    seguidos = all((b - a) % 12 == 1 for a, b in zip(meses, meses[1:]))
    if len(meses) > 1 and seguidos:
        return f"{MESES[meses[0] - 1]}–{MESES[meses[-1] - 1]}"
    return ", ".join(MESES[m - 1] for m in meses)

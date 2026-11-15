"""
app.py — Punto de entrada de ChakraSat.

Para correr:   py -m streamlit run app.py

Arma la cabecera (marca, 7 pasos y datos de la parcela), descarga los datos reales
de la NASA si hace falta y dibuja la pantalla elegida (carpeta pantallas/).
"""
import streamlit as st

st.set_page_config(page_title="ChakraSat · Rotaciones con datos NASA", page_icon="🌱", layout="wide",
                   initial_sidebar_state="collapsed")

from pantallas import (comun, inicio, p1_parcela, p2_suelo, p3_estres, p4_rotaciones,  # noqa: E402
                       p5_calendario, p6_informe)
from utils.estilos import cargar_css, franja_contexto, marca, nota, pie  # noqa: E402
from utils.geo import area_hectareas  # noqa: E402

PANTALLAS = dict(zip(comun.PASOS, [inicio.mostrar, p1_parcela.mostrar, p2_suelo.mostrar, p3_estres.mostrar,
                                   p4_rotaciones.mostrar, p5_calendario.mostrar, p6_informe.mostrar]))

cargar_css()
comun.iniciar_estado()

# ---------------- Datos de la parcela activa ----------------
pid = st.session_state.parcela
comun.asegurar_datos_reales(pid)
info = comun.parcela(pid)
lat, lon = comun.coordenadas(pid)

# ---------------- Cabecera oscura a todo lo ancho ----------------
with st.container(key="cabecera"):
    col_marca, col_pasos = st.columns([1, 2.6], vertical_alignment="center")
    with col_marca:
        marca()
    with col_pasos:
        st.segmented_control("Paso", comun.PASOS, key="paso", label_visibility="collapsed")
    if (st.session_state.paso or st.session_state._ultimo_paso) != comun.PASOS[comun.INICIO]:
        franja_contexto(info["nombre"], f"{lat:.4f}, {lon:.4f}", area_hectareas(info["feature"]), comun.meta_parcela(pid))

error = comun.error_descarga(pid)
if error:
    nota(error, "aviso")

# ---------------- Pantalla actual ----------------
PANTALLAS[st.session_state.paso or st.session_state._ultimo_paso]()
pie()

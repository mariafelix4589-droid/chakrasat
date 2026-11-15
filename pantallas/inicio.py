"""
Inicio — Página interactiva (web/index.html) dentro de la app + botones para empezar.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as componentes

from pantallas.comun import PARCELA, boton_ir, boton_siguiente, estres_parcela, meta_parcela
from utils.estilos import html, subtitulo

PASOS_HISTORIA = [
    ("#2B6F98", "1", "Parcela", "Dibújala en el mapa"),
    ("#3B8F4F", "2", "Suelo", "Lo que el satélite no ve"),
    ("#B3412A", "3", "Ventana de estrés", "Meses en que sufre"),
    ("#1F5A3D", "4", "Rotaciones", "Tres opciones comparadas"),
    ("#D9A441", "5", "Calendario", "Mes a mes"),
    ("#56675D", "6", "Informe", "Para la familia"),
]


def mostrar():
    estres, meta = estres_parcela(), meta_parcela()

    # Página interactiva: scroll dentro del recuadro. Sus botones "Abrir la app" pulsan "Empezar".
    landing = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if landing.exists():
        with st.container(key="landing"):
            componentes.html(landing.read_text(encoding="utf-8"), height=760, scrolling=True)

    with st.container(key="portada"):
        html(f"""<div class="portada">
              <p>{len(estres['serie'])} meses de datos de la NASA (abr {estres['anio_inicio']} – oct 2026)
                 para elegir la mejor rotación de cada chakra.</p>
            </div>""")
        st.write("")
        c1, c2, _ = st.columns([1, 1.2, 4])
        with c1:
            boton_siguiente(PARCELA, "Empezar", clave="inicio_empezar")
        with c2:
            boton_ir(PARCELA, "Dibujar otra zona", clave="inicio_mundo")

    subtitulo("Cómo funciona")
    pasos = "".join(f'<div style="--c:{c}"><div class="n">{n}</div><b>{t}</b><span>{d}</span></div>'
                    for c, n, t, d in PASOS_HISTORIA)
    html(f'<div class="pasos">{pasos}</div>')

    subtitulo("Datos de la NASA")
    ndvi_fuente = "MODIS 250 m" if meta.get("ndvi") else "MODIS 250 m (pendiente)"
    html(f"""<div class="fuentes-datos">
          <div class="fuente-dato" style="--c:#2B6F98"><h4>Humedad del suelo</h4><p>NASA POWER</p></div>
          <div class="fuente-dato" style="--c:#7FA6BD"><h4>Lluvia</h4><p>NASA POWER</p></div>
          <div class="fuente-dato" style="--c:#3B8F4F"><h4>Vegetación (NDVI)</h4><p>{ndvi_fuente}</p></div>
        </div>""")

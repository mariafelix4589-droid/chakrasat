"""
Pantalla 5 — Calendario de 12 meses con la Ventana de Estrés encima.
"""
import pandas as pd
import streamlit as st

from config import ROTACIONES
from pantallas.comun import INFORME, SUELO, analizar_rotaciones, boton_ir, boton_siguiente, estres_parcela
from utils.estilos import fuente, leyenda_fases, nota, titulo
from utils.graficos import CONFIG_GRAFICO, figura_calendario

TODAS = "todas"


def _etiqueta(clave):
    return "Las tres" if clave == TODAS else f"{clave}. {ROTACIONES[clave]['nombre']}"


def mostrar():
    titulo("Calendario de 2 años", "Pasa el cursor sobre un mes para ver los datos de la NASA.")

    perfil = st.session_state.perfil
    if not perfil["guardado"]:
        nota("Primero registra el perfil del suelo.", "aviso")
        boton_ir(SUELO, "Ir al perfil del suelo", clave="p5_ir")
        return

    estres = estres_parcela()
    resultados, mejor = analizar_rotaciones(perfil)

    eleccion = st.radio("Rotación", [TODAS] + list(ROTACIONES), horizontal=True, format_func=_etiqueta,
                        label_visibility="collapsed")
    claves = list(ROTACIONES) if eleccion == TODAS else [eleccion]
    calendarios = {_etiqueta(k): resultados[k]["calendario"] for k in claves}

    with st.container(border=True):
        st.plotly_chart(figura_calendario(calendarios, estres), width="stretch", config=CONFIG_GRAFICO)
        leyenda_fases()

    # Lectura en una frase
    if eleccion == TODAS:
        actual = resultados["A"]["semaforo"]["meses_desnudos"]
        mejor_desnudos = resultados[mejor]["semaforo"]["meses_desnudos"]
        if actual:
            cierre = "lo mantiene cubierto." if not mejor_desnudos else f"lo deja desnudo solo en {mejor_desnudos}."
            nota(f"La rotación actual deja el suelo desnudo en <b>{actual}</b>. "
                 f"La opción {mejor} {cierre}", "estres")
        else:
            nota(f"Ninguna deja el suelo desnudo. La opción {mejor} suma nitrógeno y biomasa.")
    else:
        sem = resultados[eleccion]["semaforo"]
        if sem["meses_desnudos"]:
            nota(f"Suelo desnudo en <b>{sem['meses_desnudos']}</b>.", "estres")
        else:
            nota("Suelo cubierto en todos los meses críticos.")

        with st.expander("Detalle mes a mes"):
            cal, pm = resultados[eleccion]["calendario"], estres["por_mes"]
            st.dataframe(pd.DataFrame({
                "Mes": cal["etiqueta"],
                "Cultivo": cal["cultivo"],
                "Fase": cal["fase_nombre"],
                "Suelo": ["Cubierto" if c else "Poco cubierto" for c in cal["cubre"]],
                "Mes crítico": ["Sí" if v else "" for v in cal["en_ventana"]],
                "Humedad frente al promedio": [f"{pm.loc[m, 'dev_smap_pct']:+.0f}%" for m in cal["mes"]],
                "NDVI frente al promedio": [f"{pm.loc[m, 'dev_ndvi_pct']:+.0f}%" if estres["tiene_ndvi"]
                                            else "pendiente" for m in cal["mes"]],
                "Nota": cal["nota"],
            }), hide_index=True, width="stretch")

    fuente("Dos años agrícolas desde abril. Maíz 110–135 días (MAG-SIPA); yuca 9 meses (INIAP / ESPAM).")

    st.write("")
    boton_siguiente(INFORME, "Preparar el informe", clave="p5_sig")

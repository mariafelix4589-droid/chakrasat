"""
Pantalla 3 — Ventana de Estrés: el corazón de la app.
"""
import streamlit as st

from config import ESTRES, MESES, ROTACION_ACTUAL, ROTACIONES
from pantallas.comun import (ROTACIONES_PASO, boton_siguiente, estres_parcela, markdown_a_html, meta_parcela,
                             rango_meses)
from utils.calendario import mes_cosecha
from utils.estilos import cifras, cinta_frecuencias, cinta_ventana, html, nota, subtitulo, titulo
from utils.estres import texto_ventana
from utils.graficos import CONFIG_GRAFICO, figura_serie, figura_ventana_promedio


def mostrar():
    estres, meta = estres_parcela(), meta_parcela()
    pm = estres["por_mes"].loc[estres["meses_ventana"]]

    titulo("Ventana de estrés", "Meses en que el suelo de esta zona se seca, año tras año.")

    html(f'<div class="cinta-titulo"><b>% de años con estrés</b>'
         f'<span>Rojo: ≥ {ESTRES["frecuencia_minima"]:.0%} de los años</span></div>')
    html(cinta_ventana(estres))

    cifras([
        (rango_meses(estres["meses_ventana"]), "meses críticos", "oxido"),
        (f"{pm['frecuencia'].mean():.0%}", "de los años con estrés (promedio "
         + ", ".join(f"{MESES[m - 1]} {estres['por_mes'].loc[m, 'frecuencia']:.0%}" for m in estres["meses_ventana"]) + ")", "oxido"),
        (f"{pm['dev_smap_pct'].mean():+.0f}%", "humedad del suelo", "rio"),
        (f"{pm['dev_ndvi_pct'].mean():+.0f}%" if estres["tiene_ndvi"] else "—", "NDVI del entorno (más sol, menos nubes)", "hoja"),
    ])
    nota(markdown_a_html(texto_ventana(estres, mes_cosecha(ROTACIONES[ROTACION_ACTUAL]))), "estres")

    secos = estres["secos"]
    if secos:
        subtitulo("En un año seco", f"Años {', '.join(str(a) for a in secos['anios'])}")
        html(cinta_frecuencias(secos["frecuencia"], secos["meses"], alto=56))
        if secos["meses"] and len(secos["meses"]) > len(estres["meses_ventana"]):
            nota(f"La ventana se alarga a <b>{rango_meses(secos['meses'])}</b>.", "aviso")

    subtitulo("Registros")
    promedio, serie = st.tabs(["Año típico", "Mes a mes"])
    with promedio:
        st.plotly_chart(figura_ventana_promedio(estres, meta), width="stretch", config=CONFIG_GRAFICO)
    with serie:
        st.plotly_chart(figura_serie(estres, meta), width="stretch", config=CONFIG_GRAFICO)


    with st.expander("Cómo se calcula"):
        st.markdown(
            f"- Percentil {estres['percentil']} histórico de humedad (y NDVI).\n"
            f"- Un mes entra en la ventana si cae bajo ese valor en ≥ {ESTRES['frecuencia_minima']:.0%} de los años "
            "(umbral). El % que se muestra es la frecuencia real de cada mes.\n"
            f"- Registros: {len(estres['serie'])} meses de NASA POWER ({estres['anio_inicio']}–{estres['anio_fin']}); "
            f"NDVI: {int(estres['serie']['ndvi'].notna().sum())} meses válidos de MODIS (el resto se descartó por nubes).\n"
            f"- Criterio usado: **{'humedad y NDVI' if estres['criterio'] == 'ambos' else 'humedad'}** "
            "(en la Amazonía el NDVI casi no cambia).\n"
            f"- Fuentes: {meta['humedad']}; {meta['lluvia']}; {meta['ndvi'] or 'NDVI pendiente'}."
        )

    st.write("")
    boton_siguiente(ROTACIONES_PASO, "Comparar rotaciones", clave="p3_sig")

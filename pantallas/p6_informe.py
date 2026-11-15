"""
Pantalla 6 — Informe para la familia agricultora (descargable e imprimible).
"""
import streamlit as st

from config import TRABAJO_FUTURO
from pantallas.comun import SUELO, analizar_rotaciones, boton_ir, coordenadas, estres_parcela, meta_parcela, parcela
from utils.estilos import nota, titulo
from utils.geo import area_hectareas
from utils.informe import generar_informe


def mostrar():
    titulo("Informe", "Una página para la familia agricultora. Ábrelo y guárdalo como PDF.")

    perfil = st.session_state.perfil
    if not perfil["guardado"]:
        nota("Primero registra el perfil del suelo.", "aviso")
        boton_ir(SUELO, "Ir al perfil del suelo", clave="p6_ir")
        return

    info = parcela()
    lat, lon = coordenadas()
    resultados, mejor = analizar_rotaciones(perfil)
    informe = generar_informe(info, lat, lon, area_hectareas(info["feature"]), perfil, estres_parcela(),
                              meta_parcela(), resultados, mejor)

    st.download_button("Descargar informe", data=informe.encode("utf-8"), type="primary",
                       file_name=f"informe_chakrasat_{st.session_state.parcela}.html", mime="text/html")
    st.write("")
    # st.iframe en versiones nuevas de Streamlit; components.html en versiones anteriores
    if hasattr(st, "iframe"):
        st.iframe(informe, height=1500)
    else:
        import streamlit.components.v1 as componentes
        componentes.html(informe, height=1500, scrolling=True)

    with st.expander("Trabajo futuro"):
        st.markdown("\n".join(f"- {item}" for item in TRABAJO_FUTURO))

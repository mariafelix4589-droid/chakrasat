"""
Pantalla 2 — Perfil de suelo (input local obligatorio).
Los satélites no miden nutrientes: la fertilidad la aporta el técnico.
"""
import streamlit as st

from config import CULTIVOS_PREVIOS, TIPOS_SUELO
from pantallas.comun import PASOS, VENTANA
from utils.estilos import html, titulo
from utils.semaforo import evaluar_perfil


def _guardar():
    """Lee los widgets, guarda el perfil y pasa a la pantalla 3."""
    ss = st.session_state
    ss.perfil = {
        "tipo_suelo": ss["w_tipo"],
        "tiene_analisis": ss["w_analisis"] == "Sí",
        "ph": ss.get("w_ph", ss.perfil["ph"]),
        "materia_organica": ss.get("w_mo", ss.perfil["materia_organica"]),
        "cultivos_previos": [c for c in CULTIVOS_PREVIOS if ss.get(f"w_cult_{c}")],
        "guardado": True,
    }
    ss.paso = PASOS[VENTANA]


def mostrar():
    titulo("Perfil del suelo", "El satélite ve cuándo está seco. Tú sabes qué tan fértil es.")

    perfil = dict(st.session_state.perfil)
    # Los campos usan keys propias; se rellenan desde el perfil guardado
    for clave, valor in {
        "w_tipo": perfil["tipo_suelo"],
        "w_analisis": "Sí" if perfil["tiene_analisis"] else "No",
        "w_ph": float(perfil["ph"]),
        "w_mo": float(perfil["materia_organica"]),
        **{f"w_cult_{c}": c in perfil["cultivos_previos"] for c in CULTIVOS_PREVIOS},
    }.items():
        st.session_state.setdefault(clave, valor)

    col_form, col_lectura = st.columns([1.2, 1], gap="large")

    with col_form, st.container(border=True):
        perfil["tipo_suelo"] = st.selectbox("Tipo de suelo", TIPOS_SUELO, key="w_tipo")
        perfil["tiene_analisis"] = st.radio("¿Hay análisis de laboratorio?", ["Sí", "No"],
                                            horizontal=True, key="w_analisis") == "Sí"
        if perfil["tiene_analisis"]:
            c1, c2 = st.columns(2)
            perfil["ph"] = c1.slider("pH aproximado", 3.5, 8.0, step=0.1, key="w_ph")
            perfil["materia_organica"] = c2.number_input("Materia orgánica (%)", 0.0, 20.0, step=0.5, key="w_mo")

        st.markdown("**Cultivos de los últimos 3 años**")
        columnas = st.columns(3)
        perfil["cultivos_previos"] = [c for i, c in enumerate(CULTIVOS_PREVIOS)
                                      if columnas[i % 3].checkbox(c, key=f"w_cult_{c}")]

        # Guardamos cada cambio para no perderlo al cambiar de pantalla
        st.session_state.perfil = {**perfil, "guardado": st.session_state.perfil["guardado"]}
        st.write("")
        st.button("Guardar perfil", type="primary", on_click=_guardar)

    with col_lectura:
        lectura = evaluar_perfil(perfil)
        items = [f"<li>{o}</li>" for o in lectura["observaciones"]]
        items += [f'<li class="brecha">{b}</li>' for b in lectura["brechas"]]
        if not items:
            items = ["<li>Sin alertas particulares para este suelo.</li>"]
        html(f'''<div class="panel"><div class="subtitulo" style="margin-top:0">Qué significa</div>
              <ul class="lectura">{"".join(items)}</ul></div>''')

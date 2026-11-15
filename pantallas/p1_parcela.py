"""
Pantalla 1 — Selección de parcela.
  - Chakras de demostración (Pastaza, Napo).
  - O cualquier zona del planeta: el técnico la DIBUJA en el mapa (polígono, rectángulo o punto).
"""
import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from pantallas.comun import (SUELO, actualizar_ndvi, actualizar_power, agregar_zona, boton_siguiente,
                             coordenadas, meta_parcela, parcelas, serie_parcela)
from utils.estilos import html, nota, titulo
from utils.geo import area_hectareas

SATELITE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
NOMBRES = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
AMARILLO = "#F2C14E"
AREA_MAXIMA_HA = 500  # más grande que esto ya no es una parcela


def _mapa(todas, actual):
    lat, lon = coordenadas(actual)
    mapa = folium.Map(location=[lat, lon], zoom_start=16, tiles=None, control_scale=True)
    folium.TileLayer(tiles=SATELITE, attr="Imágenes © Esri", name="Satélite", max_zoom=19).add_to(mapa)
    folium.TileLayer(tiles=NOMBRES, attr="© Esri", name="Nombres", overlay=True, max_zoom=19).add_to(mapa)

    for pid, info in todas.items():
        elegido = pid == actual
        folium.GeoJson(
            info["feature"],
            style_function=lambda _f, e=elegido: {"color": AMARILLO if e else "#FFFFFF", "weight": 3 if e else 2,
                                                  "fillColor": "#3B8F4F", "fillOpacity": 0.3 if e else 0.12},
            tooltip=info["nombre"],
        ).add_to(mapa)

    # Herramientas para dibujar una zona nueva (arriba a la izquierda del mapa)
    estilo = {"color": AMARILLO, "weight": 3, "fillColor": AMARILLO, "fillOpacity": 0.2}
    Draw(
        position="topleft",
        draw_options={"polygon": {"shapeOptions": estilo, "allowIntersection": False},
                      "rectangle": {"shapeOptions": estilo},
                      "marker": True, "polyline": False, "circle": False, "circlemarker": False},
        edit_options={"edit": False, "remove": True},
    ).add_to(mapa)
    return mapa


def mostrar():
    titulo("Elige la parcela", "Usa una chakra demo o dibuja la tuya en cualquier lugar del mundo.")

    todas = parcelas()
    actual = st.session_state.parcela
    col_mapa, col_ficha = st.columns([1.7, 1], gap="large")

    with col_mapa:
        elegida = st.radio("Parcelas", list(todas), horizontal=True, index=list(todas).index(actual),
                           format_func=lambda k: todas[k]["nombre"], label_visibility="collapsed")
        if elegida != actual:
            st.session_state.parcela = elegida
            st.rerun()

        html('<div class="fuente">Dibuja tu zona con <b>⬟ polígono</b>, <b>▭ rectángulo</b> o <b>📍 punto</b> '
             '(izquierda del mapa).</div>')

        respuesta = st_folium(_mapa(todas, actual), height=560, use_container_width=True, key=f"mapa_{actual}",
                              returned_objects=["all_drawings"])

        dibujos = [d for d in ((respuesta or {}).get("all_drawings") or [])
                   if d and d.get("geometry", {}).get("type") in ("Polygon", "Point")]
        if dibujos:
            geometria = dibujos[-1]["geometry"]
            if geometria["type"] == "Polygon":
                area = area_hectareas({"geometry": geometria})
                descripcion = f"Zona de <b>{area:.2f} ha</b>."
            else:
                area = 1.5
                descripcion = "Punto marcado (se analizan ~1.5 ha alrededor)."
            if area > AREA_MAXIMA_HA:
                nota(f"{area:,.0f} ha es demasiado grande. Dibuja una finca.", "aviso")
            else:
                nota(descripcion)
                nombre = st.text_input("Nombre (opcional)", placeholder="Ej.: Chakra Grefa")
                if st.button("Analizar esta zona", type="primary", key="p1_zona"):
                    agregar_zona(geometria, nombre.strip() or None)
                    st.rerun()

    with col_ficha:
        info, meta, serie = todas[actual], meta_parcela(), serie_parcela()
        lat, lon = coordenadas()
        elev = (meta.get("punto") or {}).get("elevacion_m")
        tag = lambda texto, fondo, color: (f'<span class="etiqueta-fuente" style="background:{fondo};color:{color}">'
                                           f'{texto}</span>')
        real = tag("Real", "#E7F3E9", "#1F5A3D") if meta["real"] else tag("Ejemplo", "#FBF1DC", "#7A5A12")
        ndvi = (tag("Real", "#E7F3E9", "#1F5A3D") + f"MODIS, {meta.get('ndvi_meses', '')} meses") if meta.get("ndvi") \
            else tag("Pendiente", "#EEF2EC", "#56675D") + "MODIS NDVI 250 m"
        filas = [
            ("Coordenadas", f"{lat:.4f}, {lon:.4f}"),
            ("Área", f"{area_hectareas(info['feature']):.2f} ha"),
            ("Registros", f"{len(serie)} meses, {serie['anio'].min()} a {serie['anio'].max()}"),
            ("Lluvia y humedad", f"{real}NASA POWER"),
            ("Vegetación", ndvi),
        ]
        if elev:
            filas.insert(2, ("Altitud de la celda NASA", f"{elev:.0f} m"))
        lista = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in filas)
        html(f'<div class="panel ficha"><h3>{info["nombre"]}</h3><p>{info["lugar"]}</p><dl>{lista}</dl></div>')

        st.write("")
        boton_siguiente(SUELO, "Continuar con esta parcela", clave="p1_continuar")

        with st.expander("Actualizar datos de la NASA", expanded=not meta.get("ndvi")):
            if st.button("Lluvia y humedad (segundos)", key="p1_power"):
                actualizar_power(actual)
                st.rerun()
            if st.button("NDVI satelital (10–30 min)", key="p1_ndvi"):
                barra = st.progress(0.0, text="Conectando con MODIS…")
                resultado = actualizar_ndvi(actual, barra)
                (st.success if resultado["ok"] else st.error)(resultado["mensaje"])
                if resultado["ok"]:
                    st.rerun()

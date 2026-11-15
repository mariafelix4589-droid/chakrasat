"""
estilos.py — Carga el CSS y arma los bloques visuales reutilizables (HTML).
"""
from html import escape
from pathlib import Path

import streamlit as st

from config import APP, FASES, MESES
from utils.calendario import orden_meses

RAIZ = Path(__file__).resolve().parent.parent

# Logo: una hoja dentro de una órbita (chakra + satélite)
LOGO = """<svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
  <circle cx="20" cy="20" r="18" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="1.5" stroke-dasharray="3 3"/>
  <path d="M12 27 C12 17 19 11 29 11 C29 21 23 28 13 28 Z" fill="#3B8F4F"/>
  <path d="M13 27 L24 16" stroke="#E7F3E9" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="34" cy="12" r="3" fill="#D9A441"/>
</svg>"""


def cargar_css():
    css = (RAIZ / "assets" / "estilos.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def html(contenido):
    st.markdown(contenido, unsafe_allow_html=True)


# ---------------- Textos ----------------
def titulo(texto, descripcion):
    html(f'<div class="titulo-pantalla"><h1>{texto}</h1><p>{descripcion}</p></div>')


def subtitulo(texto, detalle=""):
    html(f'<div class="subtitulo">{texto}</div>' + (f'<div class="fuente">{detalle}</div>' if detalle else ""))


def nota(contenido, tipo=""):
    clase = f" nota--{tipo}" if tipo else ""
    html(f'<div class="nota{clase}">{contenido}</div>')


def fuente(contenido):
    html(f'<div class="fuente">{contenido}</div>')


def cifras(datos):
    """datos = [(valor, etiqueta, color), …]  color: 'oxido' | 'rio' | 'hoja' | 'ocre' | ''"""
    celdas = "".join(
        f'<div class="cifra{" cifra--" + c if c else ""}"><div class="cifra__valor">{v}</div>'
        f'<div class="cifra__etiqueta">{e}</div></div>' for v, e, c in datos)
    html(f'<div class="cifras" style="--n:{len(datos)}">{celdas}</div>')


# ---------------- Cinta de 12 meses ----------------
def cinta_frecuencias(frecuencia, meses_rojos, alto=78):
    """frecuencia: Serie (mes 1–12 → 0..1). meses_rojos: meses que van en rojo óxido."""
    celdas = []
    for m in orden_meses():
        f = float(frecuencia.get(m, 0) or 0)
        rojo = m in meses_rojos
        estilo = "" if rojo else f"--fondo-celda: rgba(179, 65, 42, {0.05 + 0.45 * f:.2f});"
        celdas.append(
            f'<div class="cinta__mes" title="{MESES[m - 1]}: estrés en {f:.0%} de los años">'
            f'<div class="cinta__celda{" cinta__celda--estres" if rojo else ""}" style="--alto:{alto}px; {estilo}">'
            f'{f:.0%}</div><div class="cinta__nombre{" cinta__nombre--estres" if rojo else ""}">{MESES[m - 1]}</div></div>')
    return f'<div class="cinta">{"".join(celdas)}</div>'


def cinta_ventana(estres, alto=78):
    return cinta_frecuencias(estres["por_mes"]["frecuencia"], estres["meses_ventana"], alto)


def cinta_rotacion(calendario):
    """Cinta de una rotación: color por fase; contorno rojo = suelo desnudo en la ventana."""
    celdas, anterior = [], None
    for _, fila in calendario.iterrows():
        fase = FASES[fila["fase"]]
        palabra = fila["cultivo"].split()[0]
        palabra = palabra[:4] + "." if len(palabra) > 6 else palabra  # "Descanso" → "Desc."
        texto = escape(palabra) if fila["cultivo"] != anterior else ""
        anterior = fila["cultivo"]
        clase = (" cinta__celda--desnudo" if fila["desnudo_en_ventana"] else "") + \
                (" cinta__celda--etiqueta" if texto else "")
        marca = " cinta__marca--estres" if fila["en_ventana"] else ""
        titulo_celda = escape(f'{fila["mes_nombre"]}: {fila["cultivo"]}, {fase["nombre"].lower()}'
                              + (", suelo desnudo en la ventana" if fila["desnudo_en_ventana"] else ""))
        celdas.append(
            f'<div class="cinta__mes" title="{titulo_celda}">'
            f'<div class="cinta__celda{clase}" style="--fondo-celda:{fase["color"]}; --color-celda:{fase["texto"]}">{texto}</div>'
            f'<div class="cinta__marca{marca}"></div><div class="cinta__nombre">{"A" + str(fila["anio"]) if fila["mes_nombre"] == "Abr" else fila["mes_nombre"][0]}</div></div>')
    return f'<div class="cinta cinta--rotacion" style="grid-template-columns:repeat({len(calendario)},1fr)">{"".join(celdas)}</div>'


def leyenda_fases(con_estres=True):
    items = "".join(f'<span style="--c:{f["color"]}">{f["nombre"]}</span>' for f in FASES.values())
    if con_estres:
        items += '<span style="--c:#B3412A">Mes de la ventana de estrés</span>'
        items += '<span class="contorno">Suelo desnudo en la ventana</span>'
    html(f'<div class="leyenda">{items}</div>')


def estado(sem):
    return (f'<span class="estado"><span class="punto" style="background:{sem["hex"]}"></span>'
            f'{sem["texto"]} <small>{sem["puntaje"]} de 100</small></span>'
            f'<div class="puntaje-barra"><div style="width:{sem["puntaje"]}%; background:{sem["hex"]}"></div></div>')


# ---------------- Marco de la app ----------------
def marca():
    html(f'<div class="marca">{LOGO}<div><div class="marca__nombre">{APP["nombre"]}</div>'
         f'<div class="marca__lema">Rotaciones con datos de la NASA</div></div></div>')


def franja_contexto(nombre_parcela, ubicacion, area, meta):
    if meta["real"]:
        clima = ('<span class="punto" style="background:#5CC27A"></span>NASA POWER real', meta.get("descargado", ""))
    else:
        clima = ('<span class="punto" style="background:#D9A441"></span>Datos de ejemplo', "sin conexión")
    if meta.get("ndvi"):
        ndvi = ('<span class="punto" style="background:#5CC27A"></span>MODIS real', f'{meta.get("ndvi_meses", "")} meses')
    else:
        ndvi = ('<span class="punto" style="background:rgba(255,255,255,.4)"></span>Pendiente', "paso 1")
    html(f"""<div class="contexto">
          <div><small>Parcela</small><b>{nombre_parcela}</b></div>
          <div><small>Ubicación</small><b>{ubicacion}</b></div>
          <div><small>Área</small><b>{area:.2f} ha</b></div>
          <div><small>Lluvia y humedad</small><b>{clima[0]}</b><div class="detalle">{clima[1]}</div></div>
          <div><small>NDVI</small><b>{ndvi[0]}</b><div class="detalle">{ndvi[1]}</div></div>
        </div>""")


def pie():
    html(f"""<div class="pie">
          <div><strong>Apoya, no reemplaza, el juicio del agricultor.</strong> Validar en campo.</div>
          <div>{APP["reto"]}</div>
        </div>""")

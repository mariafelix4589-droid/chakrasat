"""
graficos.py — Gráficos Plotly con el estilo de ChakraSat (minimalista, pocos colores).

Colores fijos en toda la app:
  río (azul) = humedad del suelo · hoja (verde) = NDVI · gris = lluvia · óxido (rojo) = Ventana de Estrés
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import FASES, MESES
from utils.calendario import orden_meses

RIO, HOJA, GRIS = "#2B6F98", "#3B8F4F", "#B5CCDA"
OXIDO, OXIDO_BANDA = "#B3412A", "rgba(179, 65, 42, 0.10)"
TINTA, TINTA_2, LINEA = "#17271E", "#56675D", "#E3E9E3"
FUENTE = dict(family="Public Sans, Segoe UI, sans-serif", size=13, color=TINTA)
CONFIG_GRAFICO = {"displayModeBar": False, "responsive": True}


def _estilo(fig, alto):
    fig.update_layout(
        height=alto, font=FUENTE, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=8, r=8, t=36, b=8), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0, font=dict(size=12, color=TINTA_2)),
        hoverlabel=dict(bgcolor="white", bordercolor=LINEA, font=dict(family=FUENTE["family"], size=12)),
    )
    fig.update_xaxes(showgrid=False, linecolor=LINEA, tickfont=dict(color=TINTA_2))
    fig.update_yaxes(gridcolor=LINEA, zeroline=False, tickfont=dict(color=TINTA_2), title_font=dict(size=12))
    return fig


def _nombres(meta):
    corto = lambda texto: texto.split(" (")[0]  # "SMAP L4 (datos de ejemplo)" → "SMAP L4"
    return {
        "humedad": f"Humedad del suelo, {corto(meta['humedad'])}",
        "ndvi": f"Vegetación (NDVI), {corto(meta['ndvi'] or 'MODIS')}",
        "lluvia": f"Lluvia, {corto(meta['lluvia'])}",
        "eje_humedad": f"Humedad ({meta['humedad_unidad']})",
    }


def _dos_filas():
    return make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.64, 0.36], vertical_spacing=0.07,
                         specs=[[{"secondary_y": True}], [{"secondary_y": False}]])


def _ejes(fig, estres, nombres):
    fig.update_yaxes(title_text=nombres["eje_humedad"], title_font_color=RIO, row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="NDVI", title_font_color=HOJA, row=1, col=1, secondary_y=True,
                     showgrid=False, visible=estres["tiene_ndvi"])
    fig.update_yaxes(title_text="Lluvia (mm)", row=2, col=1)


# ---------------------------------------------------------------------------
# Pantalla 3: año típico (promedio de cada mes) con la Ventana de Estrés
# ---------------------------------------------------------------------------
def figura_ventana_promedio(estres, meta):
    pm, meses, nombres = estres["por_mes"], orden_meses(), _nombres(meta)
    x = list(range(12))
    fig = _dos_filas()

    fig.add_trace(go.Scatter(x=x, y=[pm.loc[m, "smap_media"] for m in meses], name=nombres["humedad"],
                             mode="lines+markers", line=dict(color=RIO, width=2.5), marker=dict(size=6),
                             hovertemplate="%{y:.3f}"), row=1, col=1, secondary_y=False)
    if estres["tiene_ndvi"]:
        fig.add_trace(go.Scatter(x=x, y=[pm.loc[m, "ndvi_media"] for m in meses], name=nombres["ndvi"],
                                 mode="lines+markers", line=dict(color=HOJA, width=2.5), marker=dict(size=6),
                                 hovertemplate="%{y:.2f}"), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Bar(x=x, y=[pm.loc[m, "precip_media"] for m in meses], name=nombres["lluvia"],
                         marker_color=GRIS, hovertemplate="%{y:.0f} mm"), row=2, col=1)

    for i, m in enumerate(meses):
        if m in estres["meses_ventana"]:
            fig.add_vrect(x0=i - 0.5, x1=i + 0.5, fillcolor=OXIDO_BANDA, line_width=0, layer="below")

    _estilo(fig, 440)
    fig.update_xaxes(tickvals=x, ticktext=[MESES[m - 1] for m in meses], row=2, col=1)
    _ejes(fig, estres, nombres)
    return fig


# ---------------------------------------------------------------------------
# Pantalla 3: serie completa mes a mes
# ---------------------------------------------------------------------------
def figura_serie(estres, meta):
    s, nombres = estres["serie"], _nombres(meta)
    fig = _dos_filas()
    fig.add_trace(go.Scatter(x=s["date"], y=s["smap_moisture"], name=nombres["humedad"],
                             line=dict(color=RIO, width=1.8)), row=1, col=1, secondary_y=False)
    if estres["tiene_ndvi"]:
        fig.add_trace(go.Scatter(x=s["date"], y=s["ndvi"], name=nombres["ndvi"],
                                 line=dict(color=HOJA, width=1.8)), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Bar(x=s["date"], y=s["precipitation"], name=nombres["lluvia"], marker_color=GRIS),
                  row=2, col=1)
    fig.add_hline(y=estres["umbral_smap"], line_dash="dot", line_color=RIO, line_width=1, row=1, col=1,
                  annotation_text=f"percentil {estres['percentil']}", annotation_font=dict(color=RIO, size=11))
    for fecha in s.loc[s["estres"], "date"]:
        fig.add_vrect(x0=fecha - pd.Timedelta(days=15), x1=fecha + pd.Timedelta(days=15),
                      fillcolor="rgba(179, 65, 42, 0.18)", line_width=0, layer="below")
    _estilo(fig, 440)
    _ejes(fig, estres, nombres)
    return fig


# ---------------------------------------------------------------------------
# Pantalla 5: calendario de 12 meses con la Ventana de Estrés encima
# ---------------------------------------------------------------------------
def figura_calendario(calendarios, estres):
    """calendarios: {"A. Rotación actual": DataFrame, …} → una fila por rotación."""
    fig = go.Figure()
    nombre_ventana = "Ventana de estrés"
    filas = list(calendarios.keys())[::-1] + [nombre_ventana]
    base = next(iter(calendarios.values()))

    fig.add_trace(go.Bar(
        y=[nombre_ventana] * len(base), x=[1] * len(base), base=base["orden"].tolist(), orientation="h",
        marker=dict(color=[OXIDO if v else "#F1F4F1" for v in base["en_ventana"]], line=dict(color="white", width=2)),
        hovertext=[f"{m}: {'mes crítico' if v else 'sin estrés recurrente'}"
                   for m, v in zip(base["etiqueta"], base["en_ventana"])],
        hovertemplate="%{hovertext}<extra></extra>", showlegend=False))

    for nombre, cal in calendarios.items():
        for fase, info in FASES.items():
            sub = cal[cal["fase"] == fase]
            if sub.empty:
                continue
            fig.add_trace(go.Bar(
                y=[nombre] * len(sub), x=[1] * len(sub), base=sub["orden"].tolist(), orientation="h",
                showlegend=False,
                marker=dict(color=info["color"],
                            line=dict(color=[OXIDO if d else "white" for d in sub["desnudo_en_ventana"]],
                                      width=[3 if d else 2 for d in sub["desnudo_en_ventana"]])),
                text=[c.split()[0][:4] for c in sub["cultivo"]], textposition="inside", insidetextanchor="middle",
                textfont=dict(size=10, color=info["texto"]),
                hovertext=sub["tooltip"].tolist(), hovertemplate="%{hovertext}<extra></extra>"))

    for _, fila in base[base["en_ventana"]].iterrows():
        fig.add_vrect(x0=fila["orden"], x1=fila["orden"] + 1, fillcolor="rgba(179, 65, 42, 0.06)",
                      line_width=0, layer="below")

    fig.update_layout(
        barmode="overlay", bargap=0.3, height=110 + 64 * len(calendarios), font=FUENTE,
        plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=8, r=8, t=30, b=8),
        hoverlabel=dict(bgcolor="white", bordercolor=LINEA, align="left",
                        font=dict(family=FUENTE["family"], size=12)),
    )
    n = len(base)
    fig.update_xaxes(range=[0, n], tickvals=[i + 0.5 for i in range(n)],
                     ticktext=[f"<b>{m}</b><br>año {a}" if m == "Abr" else m for m, a in zip(base["mes_nombre"], base["anio"])],
                     showgrid=False, side="top", tickfont=dict(color=TINTA_2, size=11))
    for x in range(12, n, 12):
        fig.add_vline(x=x, line_color=TINTA_2, line_width=1.5)
    fig.update_yaxes(categoryorder="array", categoryarray=filas, showgrid=False, tickfont=dict(color=TINTA, size=13))
    return fig

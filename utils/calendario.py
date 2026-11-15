"""
calendario.py — Convierte una rotación de config.py en una tabla de 12 meses
y la cruza con la Ventana de Estrés.
"""
import pandas as pd

from config import ANIOS_CALENDARIO, FASES, MESES, MESES_LARGOS, MES_INICIO_AGRICOLA


def orden_meses(mes_inicio=MES_INICIO_AGRICOLA):
    """Meses en orden de año agrícola. Con inicio 4: [4, 5, …, 12, 1, 2, 3]."""
    return [((mes_inicio - 1 + i) % 12) + 1 for i in range(12)]


def _leer_registro(registro):
    """Acepta (cultivo, fase) o (cultivo, fase, {extras})."""
    cultivo, fase = registro[0], registro[1]
    extras = registro[2] if len(registro) > 2 else {}
    return cultivo, fase, extras


def generar_calendario(rotacion, estres):
    """
    Tabla de 24 filas (2 años agrícolas, desde abril) con:
      orden, anio, mes, mes_nombre, etiqueta, cultivo, fase, fase_nombre, color, cubre, nota,
      en_ventana, desnudo_en_ventana, tooltip
    """
    por_mes = estres["por_mes"]
    periodo = f"{estres['anio_inicio']}–{estres['anio_fin']}"
    meses = orden_meses() * ANIOS_CALENDARIO
    filas = []
    for orden, (mes, registro) in enumerate(zip(meses, rotacion["calendario"])):
        cultivo, fase, extras = _leer_registro(registro)
        info_fase = FASES[fase]
        cubre = extras.get("cubre", info_fase["cubre"])
        datos_mes = por_mes.loc[mes]
        en_ventana = bool(datos_mes["en_ventana"])
        anio = orden // 12 + 1

        tooltip = (
            f"<b>{MESES_LARGOS[mes - 1].capitalize()}, año {anio}</b><br>{cultivo}, {info_fase['nombre'].lower()}<br>"
            f"Humedad del suelo: {_frase_desvio(datos_mes['dev_smap_pct'])} del promedio {periodo}<br>"
            f"Lluvia: {datos_mes['precip_media']:.0f} mm/mes<br>"
            f"Suelo: {'cubierto' if cubre else 'desnudo'}"
        )
        if en_ventana:
            tooltip += "<br><b>Mes crítico</b>"
        if extras.get("nota"):
            tooltip += f"<br><i>{extras['nota']}</i>"

        filas.append({
            "orden": orden, "anio": anio, "mes": mes, "mes_nombre": MESES[mes - 1],
            "etiqueta": f"{MESES[mes - 1]} {anio}",
            "cultivo": cultivo, "fase": fase, "fase_nombre": info_fase["nombre"],
            "color": info_fase["color"], "icono": info_fase["icono"], "cubre": cubre,
            "nota": extras.get("nota", ""), "en_ventana": en_ventana,
            "desnudo_en_ventana": en_ventana and not cubre, "tooltip": tooltip,
        })
    return pd.DataFrame(filas)


def meses_desnudos_texto(calendario):
    """'Sep y Oct (años 1 y 2)' o '' si no hay meses críticos desnudos."""
    d = calendario[calendario["desnudo_en_ventana"]]
    if d.empty:
        return ""
    meses = list(dict.fromkeys(d["mes_nombre"]))
    anios = sorted(set(d["anio"]))
    return f"{' y '.join(meses)} ({'años ' + ' y '.join(map(str, anios)) if len(anios) > 1 else 'año ' + str(anios[0])})"


def _frase_desvio(pct):
    """-12.3 → '12% por debajo';  4.1 → '4% por encima'"""
    if abs(pct) < 1:
        return "igual"
    return f"{abs(pct):.0f}% {'por debajo' if pct < 0 else 'por encima'}"


def mes_cosecha(rotacion, cultivo="Maíz"):
    """Mes (1–12) en que se cosecha un cultivo en la rotación (para el texto de la ventana)."""
    for mes, registro in zip(orden_meses() * ANIOS_CALENDARIO, rotacion["calendario"]):
        if registro[0].startswith(cultivo) and registro[1] == "cosecha":
            return mes
    return None

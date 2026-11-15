"""
estres.py — Cálculo de la "Ventana de Estrés" y análisis complementarios.

Método (fácil de explicar a los jueces):
  1. Percentil 25 histórico de la humedad del suelo y del NDVI.
  2. Un mes de la serie está "en estrés" si humedad Y NDVI están bajo su percentil 25.
  3. Un mes del año entra en la Ventana si estuvo en estrés en ≥ 40 % de los años.
  4. Si con ambos criterios ningún mes llega al 40 % (pasa en la Amazonía: la vegetación casi
     no cambia), la ventana se define solo con la humedad y el NDVI queda como evidencia.

Además:
  - Escenario de años secos: la misma ventana calculada solo con los 3 años más secos.
  - Tendencias: cambio de lluvia, humedad y NDVI por década (indicativo).
"""
import numpy as np

from config import ESTRES, MESES_LARGOS


def _frecuencias(serie, columna_estres):
    return serie.groupby("mes")[columna_estres].mean().reindex(range(1, 13)).fillna(0)


def _meses_en_ventana(frecuencia, minima):
    return [int(m) for m in frecuencia.index[frecuencia >= minima]]


def calcular_ventana_estres(df, percentil=None, frecuencia_minima=None):
    percentil = percentil or ESTRES["percentil"]
    frecuencia_minima = frecuencia_minima or ESTRES["frecuencia_minima"]
    serie = df.copy()
    tiene_ndvi = bool(serie["ndvi"].notna().sum() >= 24)

    umbral_smap = serie["smap_moisture"].quantile(percentil / 100)
    serie["bajo_smap"] = serie["smap_moisture"] < umbral_smap
    umbral_ndvi = serie["ndvi"].quantile(percentil / 100) if tiene_ndvi else None
    serie["bajo_ndvi"] = serie["ndvi"] < umbral_ndvi if tiene_ndvi else False
    serie["estres_ambos"] = serie["bajo_smap"] & serie["bajo_ndvi"]

    # Criterio: ambos (lo ideal) → si no alcanza, solo humedad
    criterio = "humedad"
    if tiene_ndvi and _meses_en_ventana(_frecuencias(serie, "estres_ambos"), frecuencia_minima):
        criterio = "ambos"
    serie["estres"] = serie["estres_ambos"] if criterio == "ambos" else serie["bajo_smap"]

    por_mes = serie.groupby("mes").agg(
        frecuencia=("estres", "mean"),
        frecuencia_ambos=("estres_ambos", "mean"),
        anios=("estres", "size"),
        smap_media=("smap_moisture", "mean"),
        ndvi_media=("ndvi", "mean"),
        precip_media=("precipitation", "mean"),
    ).reindex(range(1, 13))

    por_mes["dev_smap_pct"] = (por_mes["smap_media"] / serie["smap_moisture"].mean() - 1) * 100
    por_mes["dev_ndvi_pct"] = (por_mes["ndvi_media"] / serie["ndvi"].mean() - 1) * 100 if tiene_ndvi else np.nan
    por_mes["dev_precip_pct"] = (por_mes["precip_media"] / serie["precipitation"].mean() - 1) * 100
    por_mes["en_ventana"] = por_mes["frecuencia"] >= frecuencia_minima

    meses_ventana = [int(m) for m in por_mes.index[por_mes["en_ventana"]]]
    ventana_debil = False
    if not meses_ventana:
        ventana_debil = True
        meses_ventana = [int(m) for m in por_mes["frecuencia"].nlargest(2).index]
        por_mes.loc[meses_ventana, "en_ventana"] = True

    return {
        "serie": serie,
        "por_mes": por_mes,
        "meses_ventana": orden_circular(meses_ventana),
        "ventana_debil": ventana_debil,
        "tiene_ndvi": tiene_ndvi,
        "criterio": criterio,
        "umbral_smap": umbral_smap,
        "umbral_ndvi": umbral_ndvi,
        "anio_inicio": int(serie["anio"].min()),
        "anio_fin": int(serie["anio"].max()),
        "percentil": percentil,
        "frecuencia_minima": frecuencia_minima,
        "secos": escenario_anios_secos(serie),
        "tendencias": tendencias(serie),
    }


def escenario_anios_secos(serie, cuantos=3):
    """¿Cómo se ve la ventana en los años más secos registrados? (escenario de sequía)"""
    meses_por_anio = serie.groupby("anio")["mes"].count()
    completos = meses_por_anio[meses_por_anio == 12].index
    lluvia = serie[serie["anio"].isin(completos)].groupby("anio")["precipitation"].sum()
    if len(lluvia) < cuantos + 2:
        return None
    anios_secos = sorted(int(a) for a in lluvia.nsmallest(cuantos).index)
    sub = serie[serie["anio"].isin(anios_secos)]
    frecuencia = _frecuencias(sub, "estres")
    return {
        "anios": anios_secos,
        "lluvia_anual": {int(a): float(lluvia[a]) for a in anios_secos},
        "lluvia_promedio": float(lluvia.mean()),
        "frecuencia": frecuencia,
        "meses": orden_circular(_meses_en_ventana(frecuencia, 0.5)),
    }


def tendencias(serie):
    """Pendiente lineal por década de los promedios anuales (solo años completos)."""
    meses_por_anio = serie.groupby("anio")["mes"].count()
    anual = serie[serie["anio"].isin(meses_por_anio[meses_por_anio == 12].index)].groupby("anio").agg(
        lluvia=("precipitation", "sum"), humedad=("smap_moisture", "mean"), ndvi=("ndvi", "mean"))
    resultado = {"anios": len(anual)}
    if len(anual) < 5:
        return resultado
    x = anual.index.values.astype(float)
    for columna in ["lluvia", "humedad", "ndvi"]:
        y = anual[columna].values
        if np.isnan(y).any():
            continue
        pendiente = np.polyfit(x, y, 1)[0]
        resultado[columna] = 100 * pendiente * 10 / np.mean(y)  # % por década
    return resultado


def orden_circular(meses):
    """Ordena meses que cruzan el año: [1, 2, 12] → [12, 1, 2]."""
    meses = sorted(meses)
    if len(meses) < 2:
        return meses
    saltos = [((meses[(i + 1) % len(meses)] - m) % 12, i) for i, m in enumerate(meses)]
    _, i = max(saltos)
    return meses[i + 1:] + meses[:i + 1]


def nombres_meses(meses):
    nombres = [MESES_LARGOS[m - 1] for m in meses]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def texto_ventana(resultado, mes_cosecha_actual=None):
    """Una o dos frases cortas para explicar la ventana."""
    meses = resultado["meses_ventana"]
    pm = resultado["por_mes"].loc[meses]
    texto = (f"En **{nombres_meses(meses)}** la humedad del suelo cae **{abs(pm['dev_smap_pct'].mean()):.0f}%** "
             f"en el {pm['frecuencia'].mean():.0%} de los años.")
    if resultado["tiene_ndvi"] and resultado["criterio"] == "humedad" and pm["dev_ndvi_pct"].mean() >= -2:
        texto += (" El NDVI del entorno no baja: en la temporada seca hay más sol y menos nubes, y el bosque "
                  "aguanta. Una chakra desnuda no.")
    if mes_cosecha_actual and (mes_cosecha_actual % 12) + 1 in meses:
        texto += f" Cosechar en {MESES_LARGOS[mes_cosecha_actual - 1]} deja el suelo desnudo justo ahí."
    if resultado["ventana_debil"]:
        texto += " (Señal débil: se muestran los 2 meses con más estrés.)"
    return texto

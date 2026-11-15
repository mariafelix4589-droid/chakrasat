"""
modis.py — NDVI SATELITAL REAL de MODIS (MOD13Q1, 250 m, cada 16 días).

Fuente: servicio web MODIS de ORNL DAAC (NASA). Público, SIN cuenta:
  https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset

Cómo se procesa:
  1. Se piden las imágenes de 16 días del píxel de la parcela (250 m ≈ escala de chakra).
  2. El valor viene escalado ×10 000 → se multiplica por 0.0001.
  3. Las nubes bajan el NDVI de forma falsa (la Amazonía es muy nublada). Por eso:
     a) se toma el MÁXIMO de cada mes ("composición de valor máximo", método estándar), y
     b) se descartan los meses que caen bruscamente frente a sus vecinos (filtro de nubes).
"""
import numpy as np
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

API = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
BANDA = "250m_16_days_NDVI"
ESCALA = 0.0001
# La API entrega como máximo 10 imágenes por consulta: dividimos cada año en 3 tramos
TRAMOS_DEL_ANIO = [(1, 160), (161, 320), (321, 366)]


def _urls(lat, lon, inicio, fin):
    urls = []
    for anio in range(inicio.year, fin.year + 1):
        for dia_ini, dia_fin in TRAMOS_DEL_ANIO:
            tramo_ini = date.fromordinal(date(anio, 1, 1).toordinal() + dia_ini - 1)
            if tramo_ini > fin or (anio == inicio.year and date.fromordinal(
                    date(anio, 1, 1).toordinal() + min(dia_fin, 365) - 1) < inicio):
                continue
            urls.append(f"{API}?latitude={lat:.4f}&longitude={lon:.4f}&band={BANDA}"
                        f"&startDate=A{anio}{dia_ini:03d}&endDate=A{anio}{dia_fin:03d}"
                        f"&kmAboveBelow=0&kmLeftRight=0")
    return urls


def _consultar(url, intentos=4, tiempo_max=150):
    """El servidor de ORNL a veces responde lento o con error 502: se espera y se reintenta."""
    for intento in range(intentos):
        try:
            peticion = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=tiempo_max) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if intento == intentos - 1:
                return None  # se omite este tramo; el resto de la serie sigue
            time.sleep(5 * (intento + 1))
    return None


def descargar_ndvi_mensual(lat, lon, inicio, fin, al_avanzar=None):
    """
    Devuelve una Serie mensual (índice = primer día del mes) con el NDVI máximo de cada mes.
    al_avanzar(hechos, total) sirve para mostrar una barra de progreso.
    """
    urls = _urls(lat, lon, inicio, fin)
    valores = {}
    hechos = 0
    with ThreadPoolExecutor(max_workers=2) as grupo:  # pocas a la vez: el servidor es lento
        for respuesta in grupo.map(_consultar, urls):
            hechos += 1
            if al_avanzar:
                al_avanzar(hechos, len(urls))
            for imagen in (respuesta or {}).get("subset", []):
                crudo = imagen["data"][0]
                if crudo is None or crudo < -2000:  # -3000 = sin dato
                    continue
                mes = imagen["calendar_date"][:7] + "-01"
                valores[mes] = max(valores.get(mes, -1.0), crudo * ESCALA)

    serie = pd.Series(valores, dtype=float)
    serie.index = pd.to_datetime(serie.index)
    return filtro_nubes(serie.sort_index())


def filtro_nubes(serie, caida=0.15, pasadas=2):
    """Quita los meses cuyo NDVI cae más de 0.15 por debajo de AMBOS vecinos (típico de nubes)."""
    serie = serie.dropna().sort_index()
    for _ in range(pasadas):
        v = serie.values
        conservar = np.ones(len(v), dtype=bool)
        for i in range(len(v)):
            vecinos = [v[j] for j in (i - 1, i + 1) if 0 <= j < len(v)]
            if vecinos and v[i] < min(vecinos) - caida:
                conservar[i] = False
        serie = serie[conservar]
    return serie

"""
geo.py — Lectura de polígonos y cálculo de área (sin librerías pesadas).
"""
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def cargar_parcelas(ruta="data/parcelas_demo.geojson"):
    """Devuelve {id: feature} desde el GeoJSON de parcelas de demo."""
    with open(RAIZ / ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return {feat["properties"]["id"]: feat for feat in datos["features"]}


def anillo(feature):
    """Lista de puntos (lon, lat) del borde exterior del polígono (cerrado)."""
    puntos = feature["geometry"]["coordinates"][0]
    return puntos if puntos[0] == puntos[-1] else puntos + [puntos[0]]


def centroide(feature):
    """Centro aproximado (lat, lon) del polígono."""
    puntos = anillo(feature)[:-1]
    lat = sum(p[1] for p in puntos) / len(puntos)
    lon = sum(p[0] for p in puntos) / len(puntos)
    return lat, lon


def area_hectareas(feature):
    """
    Área aproximada en hectáreas. Proyecta los puntos a metros
    (aproximación válida para parcelas pequeñas) y usa la fórmula del "cordón de zapato".
    """
    puntos = anillo(feature)
    lat0 = math.radians(centroide(feature)[0])
    xy = [(lon * 111_320 * math.cos(lat0), lat * 110_574) for lon, lat in puntos]
    area_m2 = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:]))) / 2
    return area_m2 / 10_000


def contiene(feature, lat, lon):
    """¿El punto (lat, lon) está dentro del polígono? (método del rayo)"""
    puntos = anillo(feature)
    dentro = False
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro

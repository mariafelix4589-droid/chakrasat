"""
datos.py — Cargar (o generar) la serie mensual satelital de cada parcela.

Formato EXACTO que deben tener los CSV (mock o reales):

    date,smap_moisture,ndvi,precipitation
    2015-04-01,0.452,0.842,361.2
    ...

  date           primer día del mes (AAAA-MM-01)
  smap_moisture  humedad del suelo SMAP L4, promedio mensual (m³/m³)
  ndvi           NDVI MODIS MOD13A2, promedio mensual (0 a 1)
  precipitation  lluvia GPM IMERG, acumulado mensual (mm)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS = ["date", "smap_moisture", "ndvi", "precipitation"]
RAIZ = Path(__file__).resolve().parent.parent


def generar_datos_mock(semilla=7, inicio="2015-04-01", fin="2025-12-01", meses_estres=(9, 10)):
    """
    Crea datos de ejemplo con la MISMA forma que los reales.
    Simula una parcela amazónica húmeda con una caída de humedad y NDVI
    en 'meses_estres' (más fuerte en algunos años, como en años secos).
    ⚠️ Son datos inventados para que la app funcione sin internet.
    """
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range(inicio, fin, freq="MS")  # MS = inicio de cada mes
    anios = sorted(set(fechas.year))
    # Intensidad del año: algunos años la temporada de estrés es más fuerte
    intensidad = {a: rng.uniform(0.4, 1.3) for a in anios}

    filas = []
    for f in fechas:
        m = f.month
        # Ciclo suave a lo largo del año + caída en los meses de estrés
        ciclo = np.cos(2 * np.pi * (m - 3) / 12)
        caida = intensidad[f.year] if m in meses_estres else (0.35 * intensidad[f.year] if m in (8, 11) else 0)

        humedad = 0.44 + 0.02 * ciclo - 0.09 * caida + rng.normal(0, 0.012)
        ndvi = 0.84 + 0.01 * ciclo - 0.08 * caida + rng.normal(0, 0.012)
        lluvia = 360 + 50 * ciclo - 140 * caida + rng.normal(0, 30)

        filas.append({
            "date": f.strftime("%Y-%m-%d"),
            "smap_moisture": round(float(np.clip(humedad, 0.05, 0.6)), 3),
            "ndvi": round(float(np.clip(ndvi, 0.2, 0.95)), 3),
            "precipitation": round(float(max(lluvia, 20)), 1),
        })
    return pd.DataFrame(filas, columns=COLUMNAS)


def validar(df):
    """Revisa que el CSV tenga las columnas correctas."""
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Al CSV le faltan columnas: {', '.join(faltan)}. Deben ser: {', '.join(COLUMNAS)}")
    return df


def cargar_serie(ruta_csv, semilla=7):
    """
    Lee el CSV de la parcela. Si no existe, genera datos mock y los guarda,
    así la app siempre arranca. Agrega columnas 'anio' y 'mes'.
    """
    ruta = RAIZ / ruta_csv
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        generar_datos_mock(semilla=semilla).to_csv(ruta, index=False)

    df = validar(pd.read_csv(ruta))
    df["date"] = pd.to_datetime(df["date"])
    # La humedad es obligatoria; el NDVI puede faltar (ej. datos de NASA POWER)
    df = df.sort_values("date").dropna(subset=["smap_moisture"]).reset_index(drop=True)
    df["anio"] = df["date"].dt.year
    df["mes"] = df["date"].dt.month
    return df


# ---------------------------------------------------------------------------
# Fuentes de los datos: cada CSV puede tener al lado un archivo .meta.json
# que dice de dónde vino cada columna (lo escriben los scripts de descarga).
# ---------------------------------------------------------------------------
META_MOCK = {
    "real": False,
    "humedad": "SMAP L4 (datos de ejemplo)",
    "humedad_unidad": "m³/m³",
    "ndvi": "MODIS MOD13A2 (datos de ejemplo)",
    "lluvia": "GPM IMERG (datos de ejemplo)",
    "nota": "Datos inventados con el mismo formato que los reales.",
}


def ruta_meta(ruta_csv):
    """data/serie_pastaza.csv → data/serie_pastaza.meta.json"""
    return RAIZ / str(ruta_csv).replace(".csv", ".meta.json")


def cargar_meta(ruta_csv):
    ruta = ruta_meta(ruta_csv)
    if ruta.exists():
        meta = json.loads(ruta.read_text(encoding="utf-8"))
        base = {k: v for k, v in META_MOCK.items() if k != "nota"} if meta.get("real") else META_MOCK
        return {**base, **meta}
    return dict(META_MOCK)


def fecha_modificacion(ruta_csv):
    """Sirve para que la caché se renueve cuando se descargan datos nuevos."""
    ruta = RAIZ / ruta_csv
    return ruta.stat().st_mtime if ruta.exists() else 0

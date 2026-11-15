"""
unir_datos_reales.py — Junta las descargas reales de NASA en el CSV que usa la app.

1. Guarden sus descargas en data/crudos/ con este nombre y DOS columnas (date, value):
     data/crudos/<parcela>_smap.csv    humedad SMAP L4 (diaria o mensual, m³/m³)
     data/crudos/<parcela>_ndvi.csv    NDVI MODIS MOD13A2 (cada 16 días o mensual)
     data/crudos/<parcela>_precip.csv  lluvia GPM IMERG
   (En AppEEARS/Giovanni la columna del valor tiene otro nombre: renómbrenla a "value".)

2. Corran:   python scripts/unir_datos_reales.py pastaza

3. Listo: el script escribe también el archivo .meta.json con las fuentes.

⚠️ Unidades de la lluvia:
   - Si el archivo es DIARIO en mm/día → se SUMA por mes (opción por defecto).
   - Si es IMERG MENSUAL (3IMERGM), viene en mm/hora → usen --imerg-mensual
     para multiplicar por las horas del mes.
   - NDVI de MOD13A2 suele venir escalado ×10000 (ej. 8450) → se divide solo si es > 1.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PARCELAS  # noqa: E402
from utils.datos import COLUMNAS, RAIZ, ruta_meta  # noqa: E402


def leer(ruta):
    df = pd.read_csv(ruta)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].astype(float)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parcela", choices=list(PARCELAS))
    parser.add_argument("--imerg-mensual", action="store_true", help="la lluvia es IMERG mensual en mm/h")
    args = parser.parse_args()

    crudos = RAIZ / "data" / "crudos"
    smap = leer(crudos / f"{args.parcela}_smap.csv").resample("MS").mean()
    ndvi = leer(crudos / f"{args.parcela}_ndvi.csv")
    if ndvi.max() > 1:
        ndvi = ndvi / 10000  # MOD13A2 viene escalado
    ndvi = ndvi.resample("MS").mean()

    lluvia = leer(crudos / f"{args.parcela}_precip.csv")
    if args.imerg_mensual:
        lluvia = lluvia.resample("MS").mean() * lluvia.resample("MS").mean().index.days_in_month * 24
    else:
        lluvia = lluvia.resample("MS").sum(min_count=1)

    final = pd.DataFrame({"smap_moisture": smap, "ndvi": ndvi, "precipitation": lluvia}).dropna()
    final.index.name = "date"
    final = final.reset_index()
    final["date"] = final["date"].dt.strftime("%Y-%m-%d")
    final = final.round({"smap_moisture": 3, "ndvi": 3, "precipitation": 1})[COLUMNAS]

    destino = RAIZ / PARCELAS[args.parcela]["csv"]
    final.to_csv(destino, index=False)
    print(f"✅ {destino.name}: {len(final)} meses ({final['date'].iloc[0]} → {final['date'].iloc[-1]})")
    meta = {"real": True, "descargado": date.today().isoformat(),
            "humedad": "SMAP L4 (SPL4SMGP)", "humedad_unidad": "m³/m³",
            "ndvi": "MODIS MOD13A2", "lluvia": "GPM IMERG", "nota": ""}
    ruta_meta(PARCELAS[args.parcela]["csv"]).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ Fuentes guardadas. Recarguen la app (F5).")


if __name__ == "__main__":
    main()

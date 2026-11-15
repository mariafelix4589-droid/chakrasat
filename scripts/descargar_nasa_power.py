"""
descargar_nasa_power.py — Descarga datos reales de la NASA desde la terminal.

La app ya descarga NASA POWER sola al abrirse. Este script sirve para dejar todo listo
ANTES de la demo, incluido el NDVI de MODIS (que tarda varios minutos).

Uso (en la carpeta chakrasat):
    py scripts/descargar_nasa_power.py              ← lluvia y humedad de todas las parcelas
    py scripts/descargar_nasa_power.py --ndvi       ← además NDVI satelital de MODIS
    py scripts/descargar_nasa_power.py pastaza --ndvi
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PARCELAS  # noqa: E402
from utils.geo import cargar_parcelas, centroide  # noqa: E402
from utils.nasa_power import descargar_ndvi, descargar_power  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Descarga datos reales de la NASA")
    parser.add_argument("parcelas", nargs="*", help=f"ids: {', '.join(PARCELAS)} (vacío = todas)")
    parser.add_argument("--ndvi", action="store_true", help="descargar también NDVI de MODIS (lento)")
    args = parser.parse_args()
    ids = args.parcelas or list(PARCELAS)
    if any(p not in PARCELAS for p in ids):
        parser.error(f"Opciones: {', '.join(PARCELAS)}")

    geo = cargar_parcelas()
    for pid in ids:
        lat, lon = centroide(geo[pid])
        csv = PARCELAS[pid]["csv"]
        print(f"\n{PARCELAS[pid]['nombre']}")
        try:
            print(f"  NASA POWER: {descargar_power(lat, lon, csv)} meses de lluvia y humedad.")
        except Exception as e:  # noqa: BLE001
            print(f"  NASA POWER: no se pudo descargar ({e}).")
        if args.ndvi:
            avance = lambda h, t: print(f"\r  MODIS: consulta {h} de {t}", end="", flush=True)
            try:
                print(f"\n  MODIS: {descargar_ndvi(lat, lon, csv, avance)} meses de NDVI satelital.")
            except Exception as e:  # noqa: BLE001
                print(f"\n  MODIS: no se pudo descargar ({e}). El servidor puede estar lento; reintenta más tarde.")
    print("\nRecarga la app en el navegador para ver los datos.")


if __name__ == "__main__":
    main()

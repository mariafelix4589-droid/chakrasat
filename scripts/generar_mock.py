"""
Genera (o regenera) los CSV de ejemplo de cada parcela en data/.
Uso:  python scripts/generar_mock.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PARCELAS  # noqa: E402
from utils.datos import RAIZ, cargar_meta, generar_datos_mock  # noqa: E402

for pid, p in PARCELAS.items():
    if cargar_meta(p["csv"])["real"]:
        print(f"⏭️  {pid}: tiene datos reales, no se sobrescribe")
        continue
    df = generar_datos_mock(semilla=p["semilla_mock"])
    df.to_csv(RAIZ / p["csv"], index=False)
    print(f"✅ {p['csv']}: {len(df)} meses ({df['date'].iloc[0]} → {df['date'].iloc[-1]})")

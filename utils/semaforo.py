"""
semaforo.py — Semáforo por rotación (rojo / amarillo / verde).

Puntaje de 0 a 100, sumando y restando cosas que se pueden explicar en voz alta:
  + cobertura del suelo en la Ventana de Estrés (lo más importante)
  + aporte de nitrógeno (leguminosa)
  + biomasa alta si el suelo es pobre (dato que ingresa el técnico)
  − riesgo de manejo
  − repetir lo mismo cuando el maíz ya se siembra todos los años
"""
from config import SEMAFORO, SUELOS
from utils.calendario import meses_desnudos_texto


def evaluar_perfil(perfil):
    """Lee el perfil de suelo y devuelve observaciones para el resto de la app."""
    observaciones, brechas = [], []
    suelo_pobre = False

    suelo = SUELOS.get(perfil["tipo_suelo"], SUELOS["Franco"])
    suelo_pobre = suelo["pobre"]
    observaciones.append(f"{perfil['tipo_suelo']}: {suelo['nota']}")
    if suelo.get("brecha"):
        brechas.append(suelo["brecha"])

    if perfil["tiene_analisis"]:
        if perfil["materia_organica"] < 3:
            suelo_pobre = True
            observaciones.append(f"Materia orgánica baja ({perfil['materia_organica']:.1f}%): sumar biomasa.")
        if perfil["ph"] < 5.0:
            observaciones.append(f"pH ácido ({perfil['ph']:.1f}): revisar tolerancia y encalado.")
    else:
        brechas.append("Sin análisis: fertilidad desconocida.")

    repeticion_maiz = "Maíz" in perfil["cultivos_previos"]
    if repeticion_maiz:
        observaciones.append("Maíz repetido: más plagas y desgaste.")
    if "Pasto" in perfil["cultivos_previos"]:
        observaciones.append("Venía de pasto: revisar compactación.")

    return {"suelo_pobre": suelo_pobre, "repeticion_maiz": repeticion_maiz,
            "observaciones": observaciones, "brechas": brechas}


def calcular_semaforo(rotacion, calendario, perfil):
    """Puntaje 0–100 explicable. La práctica actual parte de una base: no vale cero."""
    p = SEMAFORO
    lectura = evaluar_perfil(perfil)
    razones = [f"Base (+{p['base']})"]

    criticos = calendario[calendario["en_ventana"]]
    n = max(1, len(criticos))
    cubiertos = int(criticos["cubre"].sum())
    cobertura = cubiertos / n
    puntaje = p["base"] + p["peso_cobertura"] * cobertura
    razones.append(f"Suelo cubierto {cubiertos}/{len(criticos)} meses críticos (+{p['peso_cobertura'] * cobertura:.0f})")

    if rotacion["leguminosa"]:
        puntaje += p["bono_leguminosa"]
        razones.append(f"Leguminosa: fija nitrógeno (+{p['bono_leguminosa']})")
    if lectura["suelo_pobre"] and (rotacion["leguminosa"] or rotacion["alta_biomasa"]):
        puntaje += p["bono_suelo_pobre"]
        razones.append(f"Suelo pobre: la cobertura vale más (+{p['bono_suelo_pobre']})")
    efecto = SUELOS.get(perfil["tipo_suelo"], {}).get("desnudo")
    if cobertura < 1 and efecto:
        puntaje -= p["castigo_suelo_desnudo"]
        razones.append(f"{perfil['tipo_suelo']} sin cobertura: {efecto} (−{p['castigo_suelo_desnudo']})")
    castigo = p["castigo_riesgo"][rotacion["riesgo_manejo"]]
    if castigo:
        puntaje -= castigo
        razones.append(f"Manejo exigente (−{castigo})")
    if lectura["repeticion_maiz"] and rotacion["tipo"] == "actual":
        puntaje -= p["castigo_repeticion"]
        razones.append(f"Repite el mismo esquema (−{p['castigo_repeticion']})")

    puntaje = max(0, min(100, round(puntaje)))
    color = "verde" if puntaje >= p["umbral_verde"] else "amarillo" if puntaje >= p["umbral_amarillo"] else "rojo"
    return {
        "puntaje": puntaje, "color": color, **p["colores"][color], "razones": razones,
        "cobertura": cobertura, "cubiertos": cubiertos, "criticos": len(criticos),
        "meses_desnudos": meses_desnudos_texto(calendario),
        "perfil": lectura,
    }

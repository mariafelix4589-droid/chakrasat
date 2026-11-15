"""
config.py — Toda la configuración editable de la app en un solo lugar.

Aquí están:
  - Nombre de la app y textos fijos
  - Parcelas de demostración
  - Fases del calendario (colores)
  - Las 3 rotaciones, mes por mes, con sus textos
  - Parámetros de la Ventana de Estrés y del semáforo

Si quieren cambiar una rotación o un texto, solo editen este archivo.
"""

# ---------------------------------------------------------------------------
# 1. IDENTIDAD DE LA APP
# ---------------------------------------------------------------------------
APP = {
    "nombre": "ChakraSat",
    "subtitulo": "Comparador de rotaciones para la Amazonía ecuatoriana con datos de la NASA",
    "reto": "NASA Space Apps Challenge 2026, reto Field Shift: Adapting Farms with NASA Data",
    "aviso": (
        "Apoya, no reemplaza, el juicio del agricultor. Validar en campo."
    ),
}

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# El calendario se muestra como "año agrícola": empieza en la siembra del maíz.
MES_INICIO_AGRICOLA = 4  # 4 = abril
ANIOS_CALENDARIO = 2      # el calendario muestra 2 años agrícolas (24 meses)

# ---------------------------------------------------------------------------
# 2. PARCELAS DE DEMOSTRACIÓN
# Los polígonos están en data/parcelas_demo.geojson (coordenadas APROXIMADAS:
# reemplazar por la chakra real). Cada parcela tiene su CSV de datos satelitales
# y, si son reales, un archivo .meta.json al lado que dice de dónde vienen.
# ---------------------------------------------------------------------------
PARCELAS = {
    "pastaza": {
        "nombre": "Chakra de demostración, Pastaza",
        "lugar": "Cerca de Puyo, Pastaza (coordenadas aproximadas)",
        "csv": "data/serie_pastaza.csv",
        "semilla_mock": 7,      # para generar datos de ejemplo si no hay CSV
    },
    "napo": {
        "nombre": "Chakra de demostración, Napo",
        "lugar": "Cerca de Tena, Napo (coordenadas aproximadas)",
        "csv": "data/serie_napo.csv",
        "semilla_mock": 21,
    },
}
PARCELA_INICIAL = "pastaza"

# ---------------------------------------------------------------------------
# 3. FASES DEL CALENDARIO
# "cubre": si en esa fase el suelo normalmente está protegido por plantas.
# ---------------------------------------------------------------------------
FASES = {
    "siembra":     {"nombre": "Siembra",     "color": "#B9D7B0", "texto": "#1B2E24", "icono": "🌱", "cubre": False},
    "crecimiento": {"nombre": "Crecimiento", "color": "#3B8F4F", "texto": "#FFFFFF", "icono": "🌿", "cubre": True},
    "cosecha":     {"nombre": "Cosecha",     "color": "#D9A441", "texto": "#1B2E24", "icono": "🧺", "cubre": True},
    "barbecho":    {"nombre": "Descanso",    "color": "#E4DACD", "texto": "#6B5A49", "icono": "🟫", "cubre": False},
    "mulch":       {"nombre": "Mulch",       "color": "#9C8A5E", "texto": "#FFFFFF", "icono": "🍂", "cubre": True},
}

# ---------------------------------------------------------------------------
# 4. LAS 3 ROTACIONES
# "calendario": un registro por mes (1 = enero … 12 = diciembre).
#   (cultivo, fase)  o  (cultivo, fase, {"cubre": True, "nota": "..."}) para excepciones.
# Textos: por qué / evidencia / beneficio / brecha / riesgo (requisito del reto).
# Los valores agronómicos son REFERENCIALES y deben validarse localmente.
# ---------------------------------------------------------------------------
# Calendario de 2 AÑOS AGRÍCOLAS (abril del año 1 → marzo del año 3), un registro por mes.
# Duraciones según el equipo (Tiempos_Produccion_Cultivos_Napo_Pastaza.xlsx):
#   maíz duro seco 110–135 días (MAG-SIPA) → siembra abr, cosecha ago
#   yuca 6–12 meses, promedio 9 (INIAP / ESPAM) → siembra nov, cosecha jul del año 2
# Registro: (cultivo, fase)  o  (cultivo, fase, {"cubre": True, "nota": "..."})
def _maiz(acompanante=None, nota=None):
    julio = ("Maíz + " + acompanante, "crecimiento", {"nota": nota}) if acompanante else ("Maíz", "crecimiento")
    agosto = ("Maíz + " + acompanante, "cosecha") if acompanante else ("Maíz", "cosecha")
    return [("Maíz", "siembra"), ("Maíz", "crecimiento"), ("Maíz", "crecimiento"), julio, agosto]


def _yuca(acompanante=None):
    nombre = "Yuca + " + acompanante if acompanante else "Yuca"
    return [(nombre, "crecimiento")] * 7 + [(nombre, "cosecha", {"nota": "Cosecha de yuca a los 9 meses."})]


ROTACIONES = {
    "A": {
        "nombre": "Rotación actual",
        "secuencia": "Maíz → Descanso → Yuca → Descanso",
        "icono": "🌽", "tipo": "actual", "leguminosa": False, "alta_biomasa": False, "riesgo_manejo": "bajo",
        "calendario": _maiz() + [("Descanso", "barbecho")] * 2 + [("Yuca", "siembra")] + _yuca()
                      + [("Descanso", "barbecho")] * 8,
        "por_que": "Es lo que se siembra hoy: punto de comparación.",
        "beneficio": "Manejo conocido, sin costos nuevos.",
        "brecha": "Se desconoce cuánta maleza cubre el descanso.",
        "riesgo": "Suelo desnudo en meses secos: pierde humedad y materia orgánica.",
    },
    "B": {
        "nombre": "Con leguminosa",
        "secuencia": "Maíz → Maní forrajero (perenne) → Yuca + maní",
        "icono": "🥜", "tipo": "leguminosa", "leguminosa": True, "alta_biomasa": False, "riesgo_manejo": "bajo",
        "calendario": _maiz("maní", "Maní forrajero sembrado entre el maíz: llega establecido a septiembre.")
                      + [("Maní", "crecimiento")] * 2
                      + [("Yuca + maní", "siembra", {"cubre": True, "nota": "Yuca sembrada sobre el maní vivo."})]
                      + _yuca("maní") + [("Maní", "crecimiento", {"nota": "El maní es perenne: sigue cubriendo."})] * 8,
        "por_que": "Una leguminosa perenne cubre el suelo todo el tiempo.",
        "beneficio": "Fija nitrógeno y protege el suelo en los dos años.",
        "brecha": "Establecimiento lento: sembrarlo entre el maíz en julio.",
        "riesgo": "Requiere semilla o esquejes en la zona.",
    },
    "C": {
        "nombre": "Con cobertura",
        "secuencia": "Maíz → Mucuna → Yuca → Mucuna",
        "icono": "🍃", "tipo": "cobertura", "leguminosa": True, "alta_biomasa": True, "riesgo_manejo": "medio",
        "calendario": _maiz("mucuna", "Mucuna sembrada en relevo entre el maíz.")
                      + [("Mucuna", "crecimiento")] * 2
                      + [("Yuca", "siembra", {"cubre": True, "nota": "Mucuna cortada: queda como mulch."})]
                      + _yuca()[:6] + [("Yuca + mucuna", "crecimiento", {"nota": "Mucuna en relevo antes de cosechar."})]
                      + [("Yuca + mucuna", "cosecha")]
                      + [("Mucuna", "crecimiento")] * 3
                      + [("Mulch", "mulch")] * 2 + [("Descanso", "barbecho")] * 3,
        "por_que": "La mucuna cubre rápido y deja mulch para la yuca.",
        "beneficio": "Mucha materia orgánica y nitrógeno.",
        "brecha": "Sin datos locales de mucuna en esta parroquia.",
        "riesgo": "Es trepadora: hay que cortarla a tiempo.",
    },
}
for _r in ROTACIONES.values():
    assert len(_r["calendario"]) == 24, _r["nombre"]
ROTACION_ACTUAL = "A"

# ---------------------------------------------------------------------------
# 5. VENTANA DE ESTRÉS
# Un mes del año entra en la ventana si, en suficientes años, la humedad SMAP
# Y el NDVI estuvieron por debajo del percentil 25 histórico al mismo tiempo.
# ---------------------------------------------------------------------------
ESTRES = {
    "percentil": 25,
    "frecuencia_minima": 0.4,  # en al menos 40% de los años
    "anio_inicio": 2015,
    "anio_fin": 2025,
}

# ---------------------------------------------------------------------------
# 6. SEMÁFORO (puntaje de 0 a 100)
# ---------------------------------------------------------------------------
SEMAFORO = {
    "base": 40,                  # toda práctica parte con puntos: la actual no vale cero
    "peso_cobertura": 40,        # % de meses críticos con suelo cubierto × 40
    "bono_leguminosa": 15,       # aporta nitrógeno
    "bono_suelo_pobre": 10,      # suelo arenoso o MO < 3 %: la cobertura vale más
    "castigo_suelo_desnudo": 5,  # arcilloso se compacta / arenoso se lava si queda desnudo
    "castigo_riesgo": {"bajo": 0, "medio": 10, "alto": 20},
    "castigo_repeticion": 5,     # maíz en los últimos 3 años y la rotación no cambia nada
    "umbral_verde": 70,
    "umbral_amarillo": 45,
    "colores": {
        "verde": {"hex": "#3B8F4F", "texto": "Recomendable", "icono": "🟢"},
        "amarillo": {"hex": "#C98A12", "texto": "Con cuidado", "icono": "🟡"},
        "rojo": {"hex": "#B3412A", "texto": "Mejorable", "icono": "🔴"},
    },
}

# ---------------------------------------------------------------------------
# 7. PERFIL DE SUELO (input local del técnico)
# ---------------------------------------------------------------------------
# Tipos de suelo: qué significa, qué le pasa si queda desnudo y si cuenta como "suelo pobre"
SUELOS = {
    "Arcilloso": {"nota": "retiene agua, pero se compacta.", "desnudo": "se compacta", "pobre": False},
    "Franco": {"nota": "equilibrado: buena base para rotar.", "desnudo": None, "pobre": False},
    "Arenoso": {"nota": "retiene poca agua. La cobertura ayuda mucho.", "desnudo": "se lava", "pobre": True},
    "Limoso": {"nota": "fértil, pero forma costra y se erosiona.", "desnudo": "forma costra", "pobre": False},
    "Orgánico": {"nota": "rico en materia orgánica; desnudo la pierde rápido.", "desnudo": "pierde materia orgánica",
                 "pobre": False},
    "Turbera": {"nota": "saturado de agua y muy ácido.", "desnudo": "se oxida y se hunde", "pobre": False,
                "brecha": "Turbera: la yuca necesita camellones o drenaje."},
    "Volcánico": {"nota": "retiene agua, pero fija el fósforo.", "desnudo": "se erosiona", "pobre": False,
                  "brecha": "Volcánico: revisar fósforo en el análisis."},
}
TIPOS_SUELO = list(SUELOS)
CULTIVOS_PREVIOS = ["Maíz", "Yuca", "Plátano", "Cacao", "Pasto"]
PERFIL_INICIAL = {
    "tipo_suelo": "Arcilloso",
    "tiene_analisis": False,
    "ph": 5.0,
    "materia_organica": 3.0,
    "cultivos_previos": ["Maíz", "Yuca"],
    "guardado": True,   # perfil de ejemplo precargado para la demo (se edita en el paso 2)
}

# ---------------------------------------------------------------------------
# 8. TRABAJO FUTURO (se muestra en la app como capa opcional, no central)
# ---------------------------------------------------------------------------
TRABAJO_FUTURO = [
    "Sumar SMAP y GPM (cuenta Earthdata).",
    "Validar en campo con cooperativas y el GAD.",
    "Calendario lunar como capa opcional a validar.",
    "Más cultivos y rotaciones.",
]

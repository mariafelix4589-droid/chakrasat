"""
informe.py — Informe de una página (HTML autocontenido) para entregar a la familia agricultora.
Se abre en cualquier navegador y se puede imprimir o guardar como PDF.
"""
from datetime import date
from html import escape

from config import APP, FASES, MESES, MESES_LARGOS
from utils.calendario import orden_meses

PASOS_VALIDACION = [
    "Hacer o actualizar un análisis de suelo (pH, materia orgánica, nitrógeno).",
    "Confirmar que hay semilla o material vegetativo de la leguminosa o cobertura en la zona.",
    "Probar primero en una parte pequeña de la chakra antes de cambiar toda la rotación.",
    "Observar la cobertura del suelo en los meses críticos y anotar el resultado de la cosecha.",
    "Revisar el resultado con el técnico al año siguiente.",
]

CSS = """
body{font-family:'Public Sans','Segoe UI',Arial,sans-serif;color:#17271E;margin:0;background:#EEF2EC}
.hoja{max-width:900px;margin:0 auto;background:#fff;padding:0 0 32px}
.cab{background:linear-gradient(120deg,#0E2A1C,#1B4A33);color:#fff;padding:28px 36px}
.cab small{opacity:.75}.cab h1{margin:6px 0 4px;font-size:28px;letter-spacing:-.02em}
.sec{padding:0 36px}h2{font-size:18px;margin:26px 0 10px;color:#0E2A1C}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:8px 10px;border-bottom:1px solid #E3E9E3;text-align:left;vertical-align:top}
th{color:#56675D;font-weight:600;background:#F7F9F6}
.cinta{display:grid;grid-template-columns:repeat(12,1fr);gap:3px;font-size:11px;text-align:center}
.cinta div div{height:30px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:700}
.reco{border-left:6px solid var(--c);background:#F5FAF5;padding:14px 18px;border-radius:0 10px 10px 0}
.reco b.t{font-size:20px;display:block;margin-bottom:4px}
.punto{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
ul{padding-left:20px}li{margin:4px 0}.nota{font-size:12px;color:#56675D}
.aviso{background:#FBF1DC;border-left:5px solid #D9A441;padding:12px 16px;border-radius:0 10px 10px 0;font-size:14px}
@media print{body{background:#fff}.hoja{max-width:none}}
"""


def _cinta_estres(estres):
    pm = estres["por_mes"]
    celdas = []
    for m in orden_meses():
        rojo = m in estres["meses_ventana"]
        fondo = "#B3412A" if rojo else f"rgba(179,65,42,{0.05 + 0.45 * float(pm.loc[m, 'frecuencia']):.2f})"
        color = "#fff" if rojo else "#56675D"
        celdas.append(f'<div><div style="background:{fondo};color:{color}">{pm.loc[m, "frecuencia"]:.0%}</div>{MESES[m - 1]}</div>')
    return f'<div class="cinta" style="grid-template-columns:repeat({len(cal)},1fr);font-size:9px">{"".join(celdas)}</div>'


def _cinta_rotacion(cal):
    celdas = []
    for _, f in cal.iterrows():
        fase = FASES[f["fase"]]
        borde = "outline:2px solid #B3412A;outline-offset:-2px;" if f["desnudo_en_ventana"] else ""
        celdas.append(f'<div><div style="background:{fase["color"]};color:{fase["texto"]};{borde}">'
                      f'{escape(f["cultivo"].split()[0][:5])}</div>{f["mes_nombre"]}</div>')
    return f'<div class="cinta" style="grid-template-columns:repeat({len(cal)},1fr);font-size:9px">{"".join(celdas)}</div>'


def generar_informe(info, lat, lon, area, perfil, estres, meta, resultados, mejor):
    r = resultados[mejor]
    rot, sem = r["rotacion"], r["semaforo"]
    meses = ", ".join(MESES_LARGOS[m - 1] for m in estres["meses_ventana"])
    pm = estres["por_mes"].loc[estres["meses_ventana"]]
    analisis = (f"pH {perfil['ph']:.1f}, materia orgánica {perfil['materia_organica']:.1f}%"
                if perfil["tiene_analisis"] else "Sin análisis de laboratorio")

    filas_comparacion = "".join(
        f"<tr><td><b>Opción {k}.</b> {v['rotacion']['nombre']}<br><span class='nota'>{v['rotacion']['secuencia']}</span></td>"
        f"<td><span class='punto' style='background:{v['semaforo']['hex']}'></span>{v['semaforo']['texto']} "
        f"({v['semaforo']['puntaje']}/100)</td>"
        f"<td>{v['semaforo']['cubiertos']} de {v['semaforo']['criticos']} (2 años)</td></tr>"
        for k, v in resultados.items())

    riesgos = "".join(f"<li>{escape(x)}</li>" for x in [rot["riesgo"], rot["brecha"]] + sem["perfil"]["brechas"])
    pasos = "".join(f"<li>{p}</li>" for p in PASOS_VALIDACION)
    ndvi = meta.get("ndvi") or "NDVI de MODIS pendiente"

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Informe ChakraSat · {escape(info['nombre'])}</title><style>{CSS}</style></head><body><div class="hoja">
<div class="cab"><small>{APP['nombre']} · Informe de rotación · {date.today():%d/%m/%Y}</small>
<h1>{escape(info['nombre'])}</h1><div>{lat:.4f}, {lon:.4f} · {area:.2f} ha · {escape(info['lugar'])}</div></div>

<div class="sec"><h2>Opción mejor puntuada para conversar con la familia</h2>
<div class="reco" style="--c:{sem['hex']}"><b class="t">Opción {mejor}: {rot['nombre']} ({rot['secuencia']})</b>
<span class="punto" style="background:{sem['hex']}"></span><b>{sem['texto']}</b>, {sem['puntaje']} de 100.<br>
{rot['por_que']} {rot['beneficio']}</div>

<h2>Meses críticos de la chakra</h2>
<p>Entre {estres['anio_inicio']} y {estres['anio_fin']}, el suelo de esta zona se secó por debajo de lo normal en
<b>{meses}</b> (en el {pm['frecuencia'].mean():.0%} de los años; la humedad baja {abs(pm['dev_smap_pct'].mean()):.0f}%).
Una buena rotación mantiene el suelo cubierto en esos meses.</p>
{_cinta_estres(estres)}
<p class="nota">Porcentaje de años con estrés en cada mes. En rojo, los meses de la ventana de estrés.</p>

<h2>Calendario sugerido (opción {mejor})</h2>{_cinta_rotacion(r['calendario'])}
<p class="nota">Dos años agrícolas desde abril. Borde rojo: suelo desnudo en un mes crítico.</p>

<h2>Comparación de las tres rotaciones</h2>
<table><tr><th>Rotación</th><th>Semáforo</th><th>Meses críticos con suelo cubierto</th></tr>{filas_comparacion}</table>

<h2>Perfil del suelo registrado</h2>
<table><tr><th>Tipo de suelo</th><td>{perfil['tipo_suelo']}</td></tr><tr><th>Análisis</th><td>{analisis}</td></tr>
<tr><th>Cultivos de los últimos 3 años</th><td>{', '.join(perfil['cultivos_previos']) or 'No registrados'}</td></tr></table>

<h2>Riesgos y vacíos de información</h2><ul>{riesgos}</ul>
<h2>Antes de decidir: validar en campo</h2><ol>{pasos}</ol>

<div class="aviso"><b>Esta herramienta apoya, no reemplaza, el juicio del agricultor.</b> Los valores agronómicos
son referenciales y deben validarse localmente con un técnico.</div>

<h2>Fuentes de datos</h2><p class="nota">Lluvia y humedad del suelo: {escape(meta['lluvia'])}; {escape(meta['humedad'])}.
Vegetación: {escape(ndvi)}. Los datos satelitales describen una zona (NASA POWER ~50 km, MODIS 250 m), no cada surco.
{APP['reto']}.</p></div></div></body></html>"""

"""
Pantalla 4 — Comparación de 3 rotaciones en una matriz alineada (2 años agrícolas).
Filas = criterios del reto. Columnas = rotaciones, con el color de su semáforo.
"""
from html import escape

import streamlit as st

from pantallas.comun import CALENDARIO, SUELO, analizar_rotaciones, boton_ir, boton_siguiente, estres_parcela, rango_meses
from utils.estilos import cinta_rotacion, estado, html, leyenda_fases, nota, titulo


def _fila(titulo_fila, celdas, mejor_idx, clase_extra="", estilos=None):
    partes = [f'<div class="fila-titulo{" esquina" if clase_extra else ""}">{titulo_fila}</div>']
    for i, contenido in enumerate(celdas):
        clase = f"col{' col--mejor' if i == mejor_idx else ''}{' ' + clase_extra if clase_extra else ''}"
        estilo = f' style="{estilos[i]}"' if estilos else ""
        partes.append(f'<div class="{clase}"{estilo}>{contenido}</div>')
    return "".join(partes)


def mostrar():
    perfil = st.session_state.perfil
    titulo("Compara las rotaciones", "¿Cuál mantiene el suelo cubierto en los meses críticos de los próximos 2 años?")

    if not perfil["guardado"]:
        nota("Primero registra el perfil del suelo.", "aviso")
        boton_ir(SUELO, "Ir al perfil del suelo", clave="p4_ir")
        return

    estres = estres_parcela()
    pm = estres["por_mes"].loc[estres["meses_ventana"]]
    criticos = rango_meses(estres["meses_ventana"])
    humedad = f"{pm['dev_smap_pct'].mean():+.0f}%"
    resultados, mejor = analizar_rotaciones(perfil)
    claves = list(resultados)
    mejor_idx = claves.index(mejor)

    cab, colores, sem_c, cintas, por_que, evid, benef, brecha, riesgo = ([] for _ in range(9))
    for clave in claves:
        r = resultados[clave]
        rot, sem, cal = r["rotacion"], r["semaforo"], r["calendario"]
        mejor_txt = '<div class="recomendada">Mejor puntuada</div>' if clave == mejor else ""
        cab.append(f'<div class="letra">Opción {clave}</div><div class="nombre">{rot["nombre"]}</div>'
                   f'<div class="secuencia">{rot["secuencia"]}</div>{mejor_txt}')
        colores.append(f"--c:{sem['hex']}")
        razones = "".join(f"<li>{escape(x)}</li>" for x in sem["razones"])
        sem_c.append(f'{estado(sem)}<details><summary>Cómo se calcula</summary><ul>{razones}</ul></details>')
        cintas.append(cinta_rotacion(cal) + f'<div class="fuente">2 años · cubierto <b>{sem["cubiertos"]}/{sem["criticos"]}</b> meses críticos</div>')
        por_que.append(rot["por_que"])
        # Evidencia: dato propio de la app para ESTA parcela (NASA POWER)
        if sem["meses_desnudos"]:
            evid.append(f"Deja el suelo desnudo en {sem['meses_desnudos']}, cuando la humedad cae {humedad} "
                        f"(NASA POWER, {estres['anio_inicio']}–{estres['anio_fin']}).")
        else:
            evid.append(f"Cubre {sem['cubiertos']}/{sem['criticos']} meses críticos ({criticos}, humedad {humedad}, "
                        f"NASA POWER {estres['anio_inicio']}–{estres['anio_fin']}).")
        benef.append(rot["beneficio"])
        brecha.append("<br>".join([rot["brecha"]] + sem["perfil"]["brechas"]))
        riesgo.append(rot["riesgo"])

    filas = "".join([
        _fila("", cab, mejor_idx, "cabecera", colores),
        _fila("Semáforo", sem_c, mejor_idx),
        _fila("2 años agrícolas", cintas, mejor_idx),
        _fila("Por qué", por_que, mejor_idx),
        _fila("Evidencia", evid, mejor_idx),
        _fila("Beneficio", benef, mejor_idx),
        _fila("Brecha", brecha, mejor_idx),
        _fila("Riesgo", riesgo, mejor_idx),
    ])
    html(f'<div class="matriz-scroll"><div class="matriz">{filas}</div></div>')
    leyenda_fases()
    html('<div class="fuente">Duraciones: maíz duro 110–135 días (MAG-SIPA); yuca 6–12 meses, se usan 9 (INIAP / ESPAM).</div>')

    st.write("")
    boton_siguiente(CALENDARIO, "Ver el calendario", clave="p4_sig")

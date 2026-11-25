"""Reportes de asistencia calculados con pandas."""

import pandas as pd

import config
from database import asistencias

COLUMNAS = ["fecha", "curso", "codigo", "estudiante", "hora", "estado"]


def cargar_datos(curso_id=None):
    """Devuelve las asistencias como DataFrame (de un curso o de todos)."""
    filas = asistencias.consultar_asistencias(curso_id=curso_id)
    return pd.DataFrame(filas, columns=COLUMNAS)


def resumen_por_estudiante(datos):
    """Una fila por estudiante con sus totales y su porcentaje de asistencia.

    Columnas: codigo, estudiante, clases, a_tiempo, tardes, ausencias, porcentaje.
    Llegar tarde cuenta como asistencia. Se ordena de mayor a menor porcentaje.
    """
    columnas = ["codigo", "estudiante", "clases", "a_tiempo", "tardes",
                "ausencias", "porcentaje"]
    if datos.empty:
        return pd.DataFrame(columns=columnas)

    # Tabla con una columna por estado y la cantidad de veces de cada estudiante.
    conteo = pd.crosstab([datos["codigo"], datos["estudiante"]], datos["estado"])
    for estado in (config.A_TIEMPO, config.TARDE, config.AUSENTE):
        if estado not in conteo.columns:
            conteo[estado] = 0

    resumen = pd.DataFrame({
        "a_tiempo": conteo[config.A_TIEMPO],
        "tardes": conteo[config.TARDE],
        "ausencias": conteo[config.AUSENTE],
    })
    resumen["clases"] = resumen.sum(axis=1)
    asistidas = resumen["a_tiempo"] + resumen["tardes"]
    resumen["porcentaje"] = (asistidas / resumen["clases"] * 100).round(1)

    resumen = resumen.reset_index()[columnas]
    return resumen.sort_values(["porcentaje", "estudiante"],
                               ascending=[False, True]).reset_index(drop=True)


def tardes_por_fecha(datos):
    """Cantidad de llegadas tarde en cada fecha con clase.

    Columnas: fecha, tardes. Incluye las fechas en las que nadie llegó tarde.
    """
    if datos.empty:
        return pd.DataFrame(columns=["fecha", "tardes"])

    es_tarde = datos["estado"] == config.TARDE
    return (es_tarde.groupby(datos["fecha"]).sum()
            .astype(int).rename("tardes").reset_index())


def estudiantes_en_alerta(datos, umbral=None):
    """Estudiantes con MÁS de `umbral` ausencias (reto opcional).

    Devuelve las filas de resumen_por_estudiante() de quienes superan el
    umbral, de más a menos ausencias.
    """
    if umbral is None:
        umbral = config.UMBRAL_FALLAS
    resumen = resumen_por_estudiante(datos)
    alerta = resumen[resumen["ausencias"] > umbral]
    return alerta.sort_values("ausencias", ascending=False).reset_index(drop=True)

"""Operaciones sobre la tabla de asistencias."""

import sqlite3

import config
from database.conexion import consultar, consultar_uno, ejecutar


def registrar(clase_id, estudiante_id, estado, hora=None):
    """Guarda la asistencia de un estudiante en una clase y devuelve su id.

    Lanza ValueError si el estudiante ya tiene una marca en esa clase.
    """
    try:
        nuevo_id, _ = ejecutar(
            "INSERT INTO asistencias (clase_id, estudiante_id, hora, estado) "
            "VALUES (?, ?, ?, ?)",
            (clase_id, estudiante_id, hora, estado),
        )
        return nuevo_id
    except sqlite3.IntegrityError:
        raise ValueError("El estudiante ya está registrado en esta clase.")


def buscar(clase_id, estudiante_id):
    """Devuelve la asistencia de un estudiante en una clase (o None si no hay)."""
    return consultar_uno(
        "SELECT * FROM asistencias WHERE clase_id = ? AND estudiante_id = ?",
        (clase_id, estudiante_id),
    )


def marcar_ausentes(clase_id):
    """Marca como ausentes a los estudiantes sin registro en la clase.

    Devuelve cuántos estudiantes quedaron ausentes.
    """
    _, cantidad = ejecutar(
        """
        INSERT INTO asistencias (clase_id, estudiante_id, hora, estado)
        SELECT ?, estudiantes.id, NULL, ?
        FROM estudiantes
        WHERE estudiantes.id NOT IN (
            SELECT estudiante_id FROM asistencias WHERE clase_id = ?
        )
        """,
        (clase_id, config.AUSENTE, clase_id),
    )
    return cantidad


def listar_por_clase(clase_id):
    """Asistencias de una clase, de la más reciente a la más antigua.

    Es la lista que se muestra en la pantalla de registro en vivo.
    """
    return consultar(
        """
        SELECT asistencias.id, estudiantes.codigo, estudiantes.nombre,
               asistencias.hora, asistencias.estado
        FROM asistencias
        JOIN estudiantes ON estudiantes.id = asistencias.estudiante_id
        WHERE asistencias.clase_id = ?
        ORDER BY asistencias.id DESC
        """,
        (clase_id,),
    )


def consultar_asistencias(estudiante_id=None, curso_id=None,
                          fecha_desde=None, fecha_hasta=None):
    """Consulta general de asistencias con filtros opcionales.

    Se usa para la pantalla de consultas, la exportación a Excel y los
    reportes. Las fechas van en formato AAAA-MM-DD.
    """
    sql = """
        SELECT clases.fecha, cursos.nombre AS curso,
               estudiantes.codigo, estudiantes.nombre AS estudiante,
               asistencias.hora, asistencias.estado
        FROM asistencias
        JOIN clases      ON clases.id = asistencias.clase_id
        JOIN cursos      ON cursos.id = clases.curso_id
        JOIN estudiantes ON estudiantes.id = asistencias.estudiante_id
        WHERE 1 = 1
    """
    parametros = []

    if estudiante_id is not None:
        sql += " AND estudiantes.id = ?"
        parametros.append(estudiante_id)
    if curso_id is not None:
        sql += " AND cursos.id = ?"
        parametros.append(curso_id)
    if fecha_desde:
        sql += " AND clases.fecha >= ?"
        parametros.append(fecha_desde)
    if fecha_hasta:
        sql += " AND clases.fecha <= ?"
        parametros.append(fecha_hasta)

    sql += " ORDER BY clases.fecha, cursos.nombre, estudiantes.nombre"
    return consultar(sql, parametros)

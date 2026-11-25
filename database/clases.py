"""Operaciones sobre la tabla de clases.

Una clase es una sesión de un curso en una fecha. Se abre para empezar a
registrar asistencia y se cierra al terminar. Solo puede haber una clase
abierta a la vez, porque hay un solo lector.
"""

from datetime import datetime

import config
from database.conexion import consultar, consultar_uno, ejecutar

_SQL_CLASE = """
    SELECT clases.*, cursos.nombre AS curso, cursos.dia,
           cursos.hora_inicio, cursos.tolerancia_min
    FROM clases
    JOIN cursos ON cursos.id = clases.curso_id
"""


def abrir(curso_id, fecha=None, hora_apertura=None):
    """Abre la clase de un curso y devuelve su id.

    Si no se indican, se usan la fecha y la hora actuales.
    """
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    hora_apertura = hora_apertura or datetime.now().strftime("%H:%M")

    abierta = clase_abierta()
    if abierta is not None:
        raise ValueError(
            f"Ya hay una clase abierta ({abierta['curso']}, {abierta['fecha']}). "
            "Ciérrela antes de abrir otra."
        )

    existente = consultar_uno(
        "SELECT id FROM clases WHERE curso_id = ? AND fecha = ?", (curso_id, fecha)
    )
    if existente is not None:
        raise ValueError("Ese curso ya tiene una clase registrada en esa fecha.")

    nuevo_id, _ = ejecutar(
        "INSERT INTO clases (curso_id, fecha, hora_apertura, estado) VALUES (?, ?, ?, ?)",
        (curso_id, fecha, hora_apertura, config.CLASE_ABIERTA),
    )
    return nuevo_id


def cerrar(clase_id, hora_cierre=None):
    """Marca una clase como cerrada."""
    hora_cierre = hora_cierre or datetime.now().strftime("%H:%M")
    ejecutar(
        "UPDATE clases SET estado = ?, hora_cierre = ? WHERE id = ?",
        (config.CLASE_CERRADA, hora_cierre, clase_id),
    )


def clase_abierta():
    """Devuelve la clase abierta en este momento (o None si no hay)."""
    return consultar_uno(
        _SQL_CLASE + " WHERE clases.estado = ?", (config.CLASE_ABIERTA,)
    )


def obtener(clase_id):
    """Devuelve una clase por su id, con los datos de su curso (o None)."""
    return consultar_uno(_SQL_CLASE + " WHERE clases.id = ?", (clase_id,))


def listar(curso_id=None):
    """Devuelve las clases (de un curso o de todos), de la más reciente a la más antigua."""
    if curso_id is None:
        return consultar(_SQL_CLASE + " ORDER BY clases.fecha DESC, clases.id DESC")
    return consultar(
        _SQL_CLASE + " WHERE clases.curso_id = ? ORDER BY clases.fecha DESC",
        (curso_id,),
    )


def eliminar(clase_id):
    """Elimina una clase junto con sus asistencias."""
    ejecutar("DELETE FROM clases WHERE id = ?", (clase_id,))

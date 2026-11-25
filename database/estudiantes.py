"""Operaciones sobre la tabla de estudiantes.

Los errores de datos (campos vacíos, código o tarjeta repetidos) se informan
con ValueError y un mensaje listo para mostrar en la interfaz.
"""

import sqlite3

from database.conexion import consultar, consultar_uno, ejecutar


def normalizar_uid(uid):
    """Deja el UID en mayúsculas y sin espacios. Devuelve None si está vacío."""
    if uid is None:
        return None
    uid = uid.strip().upper().replace(" ", "")
    return uid if uid else None


def _validar(codigo, nombre):
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()
    if not codigo:
        raise ValueError("El código del estudiante es obligatorio.")
    if not nombre:
        raise ValueError("El nombre del estudiante es obligatorio.")
    return codigo, nombre


def crear(codigo, nombre, uid_tarjeta=None):
    """Registra un estudiante y devuelve su id."""
    codigo, nombre = _validar(codigo, nombre)
    try:
        nuevo_id, _ = ejecutar(
            "INSERT INTO estudiantes (codigo, nombre, uid_tarjeta) VALUES (?, ?, ?)",
            (codigo, nombre, normalizar_uid(uid_tarjeta)),
        )
        return nuevo_id
    except sqlite3.IntegrityError:
        raise ValueError("Ya existe un estudiante con ese código o esa tarjeta.")


def actualizar(estudiante_id, codigo, nombre, uid_tarjeta=None):
    """Modifica los datos de un estudiante."""
    codigo, nombre = _validar(codigo, nombre)
    try:
        ejecutar(
            "UPDATE estudiantes SET codigo = ?, nombre = ?, uid_tarjeta = ? WHERE id = ?",
            (codigo, nombre, normalizar_uid(uid_tarjeta), estudiante_id),
        )
    except sqlite3.IntegrityError:
        raise ValueError("Ya existe otro estudiante con ese código o esa tarjeta.")


def asignar_tarjeta(estudiante_id, uid_tarjeta):
    """Asocia (o quita, si se pasa None) la tarjeta de un estudiante."""
    try:
        ejecutar(
            "UPDATE estudiantes SET uid_tarjeta = ? WHERE id = ?",
            (normalizar_uid(uid_tarjeta), estudiante_id),
        )
    except sqlite3.IntegrityError:
        raise ValueError("Esa tarjeta ya está asignada a otro estudiante.")


def eliminar(estudiante_id):
    """Elimina un estudiante junto con sus asistencias."""
    ejecutar("DELETE FROM estudiantes WHERE id = ?", (estudiante_id,))


def listar():
    """Devuelve todos los estudiantes ordenados por nombre."""
    return consultar("SELECT * FROM estudiantes ORDER BY nombre")


def obtener(estudiante_id):
    """Devuelve un estudiante por su id (o None)."""
    return consultar_uno("SELECT * FROM estudiantes WHERE id = ?", (estudiante_id,))


def buscar_por_codigo(codigo):
    """Devuelve el estudiante con ese código estudiantil (o None)."""
    return consultar_uno(
        "SELECT * FROM estudiantes WHERE codigo = ?", ((codigo or "").strip(),)
    )


def buscar_por_uid(uid_tarjeta):
    """Devuelve el estudiante dueño de una tarjeta (o None si no está registrada)."""
    uid = normalizar_uid(uid_tarjeta)
    if uid is None:
        return None
    return consultar_uno("SELECT * FROM estudiantes WHERE uid_tarjeta = ?", (uid,))

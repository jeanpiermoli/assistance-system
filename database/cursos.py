"""Operaciones sobre la tabla de cursos (nombre, día, hora de inicio, tolerancia)."""

import sqlite3
from datetime import datetime

import config
from database.conexion import consultar, consultar_uno, ejecutar


def _validar(nombre, dia, hora_inicio, tolerancia_min):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del curso es obligatorio.")

    if dia not in config.DIAS:
        raise ValueError("El día debe ser uno de: " + ", ".join(config.DIAS) + ".")

    try:
        # Acepta "7:00" o "07:00" y siempre guarda "07:00"
        hora_inicio = datetime.strptime(hora_inicio.strip(), "%H:%M").strftime("%H:%M")
    except (ValueError, AttributeError):
        raise ValueError("La hora de inicio debe tener el formato HH:MM (ej. 07:00).")

    try:
        tolerancia_min = int(tolerancia_min)
    except (ValueError, TypeError):
        raise ValueError("La tolerancia debe ser un número entero de minutos.")
    if tolerancia_min < 0:
        raise ValueError("La tolerancia no puede ser negativa.")

    return nombre, dia, hora_inicio, tolerancia_min


def crear(nombre, dia, hora_inicio, tolerancia_min=10):
    """Crea un curso y devuelve su id."""
    datos = _validar(nombre, dia, hora_inicio, tolerancia_min)
    try:
        nuevo_id, _ = ejecutar(
            "INSERT INTO cursos (nombre, dia, hora_inicio, tolerancia_min) VALUES (?, ?, ?, ?)",
            datos,
        )
        return nuevo_id
    except sqlite3.IntegrityError:
        raise ValueError("Ya existe un curso con ese nombre.")


def actualizar(curso_id, nombre, dia, hora_inicio, tolerancia_min):
    """Modifica los datos de un curso."""
    datos = _validar(nombre, dia, hora_inicio, tolerancia_min)
    try:
        ejecutar(
            "UPDATE cursos SET nombre = ?, dia = ?, hora_inicio = ?, tolerancia_min = ? "
            "WHERE id = ?",
            datos + (curso_id,),
        )
    except sqlite3.IntegrityError:
        raise ValueError("Ya existe otro curso con ese nombre.")


def eliminar(curso_id):
    """Elimina un curso junto con sus clases y asistencias."""
    ejecutar("DELETE FROM cursos WHERE id = ?", (curso_id,))


def listar():
    """Devuelve todos los cursos ordenados por nombre."""
    return consultar("SELECT * FROM cursos ORDER BY nombre")


def obtener(curso_id):
    """Devuelve un curso por su id (o None)."""
    return consultar_uno("SELECT * FROM cursos WHERE id = ?", (curso_id,))

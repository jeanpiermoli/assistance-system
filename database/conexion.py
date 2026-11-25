"""Conexión a SQLite, creación de tablas y funciones básicas de consulta.

Cada operación abre su propia conexión y la cierra al terminar. Así la base de
datos se puede usar sin problemas desde la interfaz y desde el hilo del lector.
"""

import os
import sqlite3

import config

SQL_TABLAS = """
CREATE TABLE IF NOT EXISTS estudiantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,          -- código estudiantil
    nombre      TEXT NOT NULL,
    uid_tarjeta TEXT UNIQUE                    -- UID de la tarjeta (puede faltar)
);

CREATE TABLE IF NOT EXISTS cursos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL UNIQUE,
    dia            TEXT NOT NULL,              -- Lunes, Martes, ...
    hora_inicio    TEXT NOT NULL,              -- HH:MM
    tolerancia_min INTEGER NOT NULL DEFAULT 10 -- minutos para llegar "a tiempo"
);

-- Una clase es una sesión de un curso en una fecha concreta.
CREATE TABLE IF NOT EXISTS clases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_id      INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
    fecha         TEXT NOT NULL,               -- AAAA-MM-DD
    hora_apertura TEXT NOT NULL,               -- HH:MM
    hora_cierre   TEXT,                        -- HH:MM (vacío si sigue abierta)
    estado        TEXT NOT NULL DEFAULT 'abierta'
                  CHECK (estado IN ('abierta', 'cerrada')),
    UNIQUE (curso_id, fecha)
);

CREATE TABLE IF NOT EXISTS asistencias (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    clase_id      INTEGER NOT NULL REFERENCES clases(id) ON DELETE CASCADE,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    hora          TEXT,                        -- HH:MM:SS (vacío si es ausente)
    estado        TEXT NOT NULL
                  CHECK (estado IN ('a tiempo', 'tarde', 'ausente')),
    UNIQUE (clase_id, estudiante_id)           -- una sola marca por clase
);
"""


def conectar():
    """Abre una conexión a la base de datos (crea la carpeta si no existe)."""
    os.makedirs(os.path.dirname(config.RUTA_BD), exist_ok=True)
    conexion = sqlite3.connect(config.RUTA_BD)
    conexion.row_factory = sqlite3.Row            # permite usar fila["nombre"]
    conexion.execute("PRAGMA foreign_keys = ON")  # respeta las claves foráneas
    return conexion


def crear_tablas():
    """Crea las tablas si todavía no existen."""
    conexion = conectar()
    try:
        conexion.executescript(SQL_TABLAS)
        conexion.commit()
    finally:
        conexion.close()


def ejecutar(sql, parametros=()):
    """Ejecuta un INSERT, UPDATE o DELETE.

    Devuelve una tupla (id de la última fila insertada, filas afectadas).
    """
    conexion = conectar()
    try:
        cursor = conexion.execute(sql, parametros)
        conexion.commit()
        return cursor.lastrowid, cursor.rowcount
    finally:
        conexion.close()


def consultar(sql, parametros=()):
    """Ejecuta un SELECT y devuelve todas las filas como lista de diccionarios."""
    conexion = conectar()
    try:
        filas = conexion.execute(sql, parametros).fetchall()
        return [dict(fila) for fila in filas]
    finally:
        conexion.close()


def consultar_uno(sql, parametros=()):
    """Ejecuta un SELECT y devuelve la primera fila (o None si no hay)."""
    filas = consultar(sql, parametros)
    return filas[0] if filas else None

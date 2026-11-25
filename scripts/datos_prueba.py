"""Carga datos de prueba: 20 estudiantes, 2 cursos y 8 clases ya cerradas.

Se ejecuta desde la carpeta del proyecto:
    python scripts/datos_prueba.py               (solo si la base está vacía)
    python scripts/datos_prueba.py --reiniciar   (BORRA todo y carga los datos de prueba)

Las tarjetas de los estudiantes de prueba son códigos inventados (SIM00001...).
Para usar una tarjeta real, edite el estudiante en la aplicación y pulse
«Leer tarjeta».
"""

import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database import asistencias, clases, conexion, cursos, estudiantes
from logica import asistencia

NOMBRES = [
    "Ana Gómez", "Luis Peña", "María Rodríguez", "Carlos Ruiz", "Sofía Martínez",
    "Andrés Castaño", "Valentina López", "Juan Muñoz", "Camila Torres",
    "Santiago Ramírez", "Daniela Herrera", "Felipe Cárdenas", "Laura Vélez",
    "Mateo Ospina", "Isabella Zapata", "Sebastián Arango", "Paula Quintero",
    "Nicolás Giraldo", "Manuela Ríos", "David Montoya",
]

CURSOS = [
    # nombre, día, hora de inicio, tolerancia en minutos
    ("Algoritmos y Programación", "Lunes", "07:00", 10),
    ("Sistemas Embebidos", "Miércoles", "10:00", 15),
]
CLASES_POR_CURSO = 4          # 2 cursos x 4 = 8 clases

# Estudiantes (por posición en la lista) que faltan mucho, para que aparezca
# la alerta de más de 3 fallas: posición -> número de clases a las que faltan.
FALTONES = {17: 4, 18: 5, 19: 6}


def ultimas_fechas(dia, cantidad):
    """Devuelve las últimas `cantidad` fechas (anteriores a hoy) que cayeron en `dia`."""
    numero_dia = config.DIAS.index(dia)
    fecha = datetime.now().date() - timedelta(days=1)
    fechas = []
    while len(fechas) < cantidad:
        if fecha.weekday() == numero_dia:
            fechas.append(fecha)
        fecha -= timedelta(days=1)
    return sorted(fechas)


def hay_datos():
    return bool(estudiantes.listar() or cursos.listar() or clases.listar())


def borrar_todo():
    for tabla in ("asistencias", "clases", "cursos", "estudiantes"):
        conexion.ejecutar(f"DELETE FROM {tabla}")


def cargar():
    azar = random.Random(2026)     # semilla fija: siempre salen los mismos datos

    ids_estudiantes = []
    for numero, nombre in enumerate(NOMBRES, start=1):
        ids_estudiantes.append(
            estudiantes.crear(f"2026{numero:03d}", nombre, f"SIM{numero:05d}"))

    # Lista de (id del curso, fecha) de las 8 clases, en orden de fecha.
    sesiones = []
    for nombre, dia, hora, tolerancia in CURSOS:
        curso_id = cursos.crear(nombre, dia, hora, tolerancia)
        for fecha in ultimas_fechas(dia, CLASES_POR_CURSO):
            sesiones.append((curso_id, fecha))
    sesiones.sort(key=lambda sesion: sesion[1])

    # A qué clases (por posición) falta cada "faltón".
    faltas = {posicion: set(azar.sample(range(len(sesiones)), cantidad))
              for posicion, cantidad in FALTONES.items()}

    for numero_clase, (curso_id, fecha) in enumerate(sesiones):
        curso = cursos.obtener(curso_id)
        inicio = datetime.strptime(f"{fecha} {curso['hora_inicio']}", "%Y-%m-%d %H:%M")
        apertura = inicio - timedelta(minutes=15)

        clase = asistencia.abrir_clase(curso_id, str(fecha), apertura.strftime("%H:%M"))

        for posicion, estudiante_id in enumerate(ids_estudiantes):
            if posicion in faltas:
                falta = numero_clase in faltas[posicion]
            else:
                falta = azar.random() < 0.07
            if falta:
                continue        # quedará ausente al cerrar la clase

            if azar.random() < 0.18:      # llega tarde
                minutos = curso["tolerancia_min"] + azar.randint(1, 25)
            else:                         # llega a tiempo
                minutos = azar.randint(-12, curso["tolerancia_min"])
            momento = inicio + timedelta(minutes=minutos, seconds=azar.randint(0, 59))

            estado = asistencia.calcular_estado(clase, momento)
            asistencias.registrar(clase["id"], estudiante_id, estado,
                                  momento.strftime("%H:%M:%S"))

        cierre = inicio + timedelta(hours=2)
        asistencia.cerrar_clase(clase["id"], cierre.strftime("%H:%M"))

    return len(ids_estudiantes), len(CURSOS), len(sesiones)


if __name__ == "__main__":
    conexion.crear_tablas()

    if hay_datos():
        if "--reiniciar" not in sys.argv:
            print("La base de datos ya tiene información y no se modificó.")
            print("Para BORRAR TODO y cargar los datos de prueba, ejecute:")
            print("    python scripts/datos_prueba.py --reiniciar")
            sys.exit(1)
        borrar_todo()
        print("Se borraron los datos anteriores.")

    total_estudiantes, total_cursos, total_clases = cargar()
    total_registros = len(asistencias.consultar_asistencias())
    print(f"Datos de prueba cargados: {total_estudiantes} estudiantes, "
          f"{total_cursos} cursos, {total_clases} clases y "
          f"{total_registros} registros de asistencia.")

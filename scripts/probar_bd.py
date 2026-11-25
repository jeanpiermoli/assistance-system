"""Prueba rápida de la base de datos.

Usa una base de datos temporal, así que NO toca los datos reales.
Se ejecuta desde la carpeta del proyecto:   python scripts/probar_bd.py
"""

import os
import sys
import tempfile

# Permite importar los módulos del proyecto al ejecutar este archivo directamente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

carpeta_temporal = tempfile.mkdtemp()
config.RUTA_BD = os.path.join(carpeta_temporal, "prueba.db")

from database import asistencias, clases, conexion, cursos, estudiantes


def debe_fallar(descripcion, funcion, *argumentos):
    """Comprueba que una operación inválida sea rechazada con ValueError."""
    try:
        funcion(*argumentos)
    except ValueError as error:
        print(f"  OK  {descripcion}: {error}")
        return
    raise AssertionError(f"Debió fallar: {descripcion}")


conexion.crear_tablas()
print("Tablas creadas.\n")

print("Estudiantes")
ana = estudiantes.crear("2024001", "Ana Gómez", "a1 b2 c3 d4")
luis = estudiantes.crear("2024002", "Luis Peña")
estudiantes.asignar_tarjeta(luis, "11223344")
assert estudiantes.buscar_por_uid("A1B2C3D4")["nombre"] == "Ana Gómez"
assert estudiantes.buscar_por_uid("FFFFFFFF") is None
assert len(estudiantes.listar()) == 2
print("  OK  crear, asignar tarjeta, buscar por UID y listar")
debe_fallar("código repetido", estudiantes.crear, "2024001", "Otro")
debe_fallar("tarjeta repetida", estudiantes.asignar_tarjeta, luis, "A1B2C3D4")
debe_fallar("nombre vacío", estudiantes.crear, "2024003", "  ")

print("\nCursos")
curso = cursos.crear("Algoritmos y Programación", "Lunes", "7:00", 10)
assert cursos.obtener(curso)["hora_inicio"] == "07:00"
print("  OK  crear curso (la hora 7:00 se guarda como 07:00)")
debe_fallar("curso repetido", cursos.crear, "Algoritmos y Programación", "Martes", "08:00", 5)
debe_fallar("hora inválida", cursos.crear, "Física", "Lunes", "25:99", 5)
debe_fallar("día inválido", cursos.crear, "Física", "Lunez", "08:00", 5)

print("\nClases y asistencias")
clase = clases.abrir(curso, "2026-11-23", "06:55")
assert clases.clase_abierta()["curso"] == "Algoritmos y Programación"
debe_fallar("dos clases abiertas a la vez", clases.abrir, curso, "2026-11-30")

asistencias.registrar(clase, ana, config.A_TIEMPO, "07:02:10")
debe_fallar("lectura repetida en la misma clase",
            asistencias.registrar, clase, ana, config.TARDE, "07:30:00")

ausentes = asistencias.marcar_ausentes(clase)
clases.cerrar(clase, "09:00")
assert ausentes == 1
assert clases.clase_abierta() is None
assert asistencias.buscar(clase, luis)["estado"] == config.AUSENTE
print("  OK  abrir clase, registrar, marcar ausentes y cerrar")

debe_fallar("misma clase dos veces", clases.abrir, curso, "2026-11-23")

print("\nConsulta general")
for fila in asistencias.consultar_asistencias(curso_id=curso):
    print("  ", fila)
assert len(asistencias.consultar_asistencias(estudiante_id=ana)) == 1
assert len(asistencias.consultar_asistencias(fecha_desde="2026-12-01")) == 0

estudiantes.eliminar(ana)
assert len(asistencias.listar_por_clase(clase)) == 1
print("\n  OK  al eliminar un estudiante se eliminan sus asistencias")

print("\nTODAS LAS PRUEBAS PASARON")

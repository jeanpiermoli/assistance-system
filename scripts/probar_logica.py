"""Prueba rápida de las reglas de asistencia.

Usa una base de datos temporal, así que NO toca los datos reales.
Se ejecuta desde la carpeta del proyecto:   python scripts/probar_logica.py
"""

import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

config.RUTA_BD = os.path.join(tempfile.mkdtemp(), "prueba.db")

from database import asistencias, conexion, cursos, estudiantes
from logica import asistencia


def a_las(hora):
    """Devuelve el día de la clase de prueba a la hora indicada (HH:MM:SS)."""
    return datetime.strptime(f"2026-11-23 {hora}", "%Y-%m-%d %H:%M:%S")


def mostrar(resultado):
    print(f"  {'ACEPTADA ' if resultado.aceptada else 'RECHAZADA'} | "
          f"{resultado.mensaje}  ->  {resultado.comando_serial()}")


conexion.crear_tablas()
estudiantes.crear("2024001", "Ana Gómez", "A1B2C3D4")
estudiantes.crear("2024002", "Luis Peña", "11223344")
estudiantes.crear("2024003", "María Rodríguez", "AABBCCDD")
estudiantes.crear("2024004", "Carlos Ruiz")            # sin tarjeta
curso = cursos.crear("Algoritmos", "Lunes", "07:00", 10)

print("Sin clase abierta")
r = asistencia.registrar_lectura("A1B2C3D4", a_las("06:58:00"))
mostrar(r)
assert not r.aceptada

clase = asistencia.abrir_clase(curso, "2026-11-23", "06:50")
print(f"\nClase abierta: {clase['curso']} {clase['fecha']} "
      f"(inicio {clase['hora_inicio']}, tolerancia {clase['tolerancia_min']} min)")

r = asistencia.registrar_lectura("a1b2c3d4", a_las("06:58:00"))   # antes de la hora
mostrar(r)
assert r.aceptada and r.estado == config.A_TIEMPO

r = asistencia.registrar_lectura("11223344", a_las("07:10:45"))   # último minuto
mostrar(r)
assert r.aceptada and r.estado == config.A_TIEMPO

r = asistencia.registrar_lectura("AABBCCDD", a_las("07:11:00"))   # pasada la tolerancia
mostrar(r)
assert r.aceptada and r.estado == config.TARDE

r = asistencia.registrar_lectura("A1B2C3D4", a_las("07:15:00"))   # repetida
mostrar(r)
assert not r.aceptada and r.linea2 == "YA REGISTRADO"

r = asistencia.registrar_lectura("FFFFFFFF", a_las("07:16:00"))   # desconocida
mostrar(r)
assert not r.aceptada and r.linea2 == "NO REGISTRADA"

r = asistencia.registrar_lectura("2024004", a_las("07:17:00"))    # código, sin permiso
assert not r.aceptada

print("\nResumen antes de cerrar:", asistencia.resumen_clase(clase["id"]))
assert asistencia.resumen_clase(clase["id"])["pendientes"] == 1

ausentes = asistencia.cerrar_clase(clase["id"], "09:00")
print(f"Clase cerrada: {ausentes} ausente(s)")
assert ausentes == 1
print("Resumen al cerrar:      ", asistencia.resumen_clase(clase["id"]))

try:
    asistencia.cerrar_clase(clase["id"])
    raise AssertionError("No debió permitir cerrar dos veces")
except ValueError as error:
    print(f"  OK  cerrar dos veces: {error}")

print("\nModo simulación con código estudiantil")
asistencia.abrir_clase(curso, "2026-11-30", "06:50")
r = asistencia.registrar_lectura("2024004", datetime(2026, 11, 30, 7, 30),
                                 permitir_codigo_estudiantil=True)
mostrar(r)
assert r.aceptada and r.estado == config.TARDE

assert len(asistencias.consultar_asistencias()) == 5
print("\nTODAS LAS PRUEBAS PASARON")

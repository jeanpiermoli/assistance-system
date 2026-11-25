"""Configuración general del sistema de asistencia con RFID."""

import os

# Carpeta del proyecto (donde está este archivo)
CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))

# Base de datos SQLite
CARPETA_DATOS = os.path.join(CARPETA_PROYECTO, "data")
RUTA_BD = os.path.join(CARPETA_DATOS, "asistencia.db")
CARPETA_EXPORTES = os.path.join(CARPETA_DATOS, "exportes")

# Comunicación con el ESP32
PUERTO_SERIAL = "COM10"     # se podrá cambiar desde la aplicación
BAUDIOS = 115200

# Estados posibles de una asistencia
A_TIEMPO = "a tiempo"
TARDE = "tarde"
AUSENTE = "ausente"

# Estados posibles de una clase
CLASE_ABIERTA = "abierta"
CLASE_CERRADA = "cerrada"

# Reto opcional: se alerta a los estudiantes con MÁS de este número de fallas
UMBRAL_FALLAS = 3

# Días de la semana (en el mismo orden que datetime.weekday(): lunes = 0)
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

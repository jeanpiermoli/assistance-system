"""Reglas de la asistencia.

Aquí se decide qué pasa con cada lectura de tarjeta: si se acepta o se rechaza,
si el estudiante llegó a tiempo o tarde, y qué ocurre al cerrar la clase.
Este módulo no sabe nada de la interfaz ni del lector: recibe un código y
devuelve un Resultado. Por eso el lector real y el modo simulación usan
exactamente la misma función.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import config
from database import asistencias, clases, estudiantes


@dataclass
class Resultado:
    """Resultado de procesar una lectura de tarjeta."""

    aceptada: bool            # True = LED verde, False = LED rojo
    mensaje: str              # texto completo para mostrar en la aplicación
    linea1: str               # primera línea del LCD (máximo 16 caracteres)
    linea2: str               # segunda línea del LCD (máximo 16 caracteres)
    estudiante: dict = None   # datos del estudiante (None si no se identificó)
    estado: str = None        # "a tiempo" o "tarde" (None si fue rechazada)
    hora: str = None          # hora de la lectura, HH:MM:SS

    def comando_serial(self):
        """Texto que se envía al ESP32, según el protocolo: OK:... o ERR:..."""
        prefijo = "OK" if self.aceptada else "ERR"
        return f"{prefijo}:{self.linea1}|{self.linea2}"


def calcular_estado(clase, momento):
    """Devuelve "a tiempo" o "tarde" según el horario del curso.

    Se llega a tiempo hasta la hora de inicio más los minutos de tolerancia
    (incluido ese último minuto). Después de eso, es tarde.
    """
    inicio = datetime.strptime(
        f"{clase['fecha']} {clase['hora_inicio']}", "%Y-%m-%d %H:%M"
    )
    limite = inicio + timedelta(minutes=clase["tolerancia_min"])

    # Se comparan solo horas y minutos: 07:10:45 todavía cuenta como 07:10.
    momento = momento.replace(second=0, microsecond=0)
    return config.A_TIEMPO if momento <= limite else config.TARDE


def registrar_lectura(codigo, momento=None, permitir_codigo_estudiantil=False):
    """Procesa una lectura y devuelve un Resultado.

    codigo:  UID de la tarjeta (del lector o escrito en modo simulación).
    momento: fecha y hora de la lectura; si no se indica, es ahora.
    permitir_codigo_estudiantil: en modo simulación también se acepta escribir
             el código estudiantil en lugar del UID de la tarjeta.
    """
    momento = momento or datetime.now()
    hora = momento.strftime("%H:%M:%S")
    hora_corta = momento.strftime("%H:%M")

    # 1. Debe haber una clase abierta.
    clase = clases.clase_abierta()
    if clase is None:
        return Resultado(False, "No hay ninguna clase abierta.",
                         "No hay clase", "abierta", hora=hora)

    # 2. La tarjeta debe pertenecer a un estudiante registrado.
    estudiante = estudiantes.buscar_por_uid(codigo)
    if estudiante is None and permitir_codigo_estudiantil:
        estudiante = estudiantes.buscar_por_codigo(codigo)
    if estudiante is None:
        codigo_limpio = (codigo or "").strip().upper()
        return Resultado(False, f"Tarjeta no registrada ({codigo_limpio}).",
                         "Tarjeta", "NO REGISTRADA", hora=hora)

    # 3. No se permite registrar dos veces a la misma persona en la misma clase.
    anterior = asistencias.buscar(clase["id"], estudiante["id"])
    if anterior is not None:
        return Resultado(
            False,
            f"{estudiante['nombre']} ya estaba registrado en esta clase "
            f"({anterior['estado']}, {anterior['hora']}).",
            estudiante["nombre"], "YA REGISTRADO",
            estudiante=estudiante, hora=hora,
        )

    # 4. Lectura válida: se guarda como "a tiempo" o "tarde".
    estado = calcular_estado(clase, momento)
    asistencias.registrar(clase["id"], estudiante["id"], estado, hora)
    return Resultado(
        True,
        f"{estudiante['nombre']} - {estado} ({hora_corta})",
        estudiante["nombre"], f"{estado.upper()} {hora_corta}",
        estudiante=estudiante, estado=estado, hora=hora,
    )


def abrir_clase(curso_id, fecha=None, hora_apertura=None):
    """Abre la clase de un curso y devuelve sus datos."""
    clase_id = clases.abrir(curso_id, fecha, hora_apertura)
    return clases.obtener(clase_id)


def cerrar_clase(clase_id, hora_cierre=None):
    """Cierra la clase y marca como ausentes a quienes no pasaron la tarjeta.

    Devuelve la cantidad de estudiantes que quedaron ausentes.
    """
    clase = clases.obtener(clase_id)
    if clase is None:
        raise ValueError("La clase no existe.")
    if clase["estado"] == config.CLASE_CERRADA:
        raise ValueError("La clase ya estaba cerrada.")

    ausentes = asistencias.marcar_ausentes(clase_id)
    clases.cerrar(clase_id, hora_cierre)
    return ausentes


def resumen_clase(clase_id):
    """Cuenta cuántos estudiantes hay en cada estado dentro de una clase.

    Devuelve, por ejemplo: {"a tiempo": 12, "tarde": 3, "ausente": 0,
    "pendientes": 5}. Los pendientes son quienes aún no han pasado la tarjeta.
    """
    resumen = {config.A_TIEMPO: 0, config.TARDE: 0, config.AUSENTE: 0}
    for fila in asistencias.listar_por_clase(clase_id):
        resumen[fila["estado"]] += 1

    registrados = sum(resumen.values())
    resumen["pendientes"] = len(estudiantes.listar()) - registrados
    return resumen

"""Comunicación serial con el ESP32.

Un hilo en segundo plano escucha el puerto todo el tiempo, para que la ventana
de la aplicación nunca se quede congelada esperando una tarjeta. Lo que llega
del ESP32 se guarda como "eventos" en una cola; la interfaz revisa esa cola
cada cierto tiempo con obtener_eventos().

Protocolo (cada mensaje es una línea terminada en salto de línea):
    ESP32 -> Python:  READY | UID:A1B2C3D4 | PONG
    Python -> ESP32:  OK:linea1|linea2 | ERR:linea1|linea2 | MSG:linea1|linea2 | PING
"""

import queue
import threading

import serial
import serial.tools.list_ports

import config

# Tipos de evento que puede entregar el lector
EVENTO_UID = "uid"                    # dato: el UID leído, ej. "A1B2C3D4"
EVENTO_LISTO = "listo"                # el ESP32 arrancó y está listo
EVENTO_PONG = "pong"                  # respuesta a un PING
EVENTO_DESCONECTADO = "desconectado"  # dato: motivo de la desconexión


def listar_puertos():
    """Devuelve los puertos seriales disponibles como lista de (puerto, descripción)."""
    return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


class LectorSerial:
    """Conexión con el lector RFID."""

    def __init__(self):
        self.eventos = queue.Queue()
        self.puerto = None
        self._serial = None
        self._hilo = None
        self._detener = threading.Event()
        self._candado = threading.Lock()   # evita que dos envíos se mezclen

    @property
    def conectado(self):
        return self._serial is not None and self._serial.is_open

    def conectar(self, puerto=None, baudios=None):
        """Abre el puerto y empieza a escuchar. Lanza ConnectionError si no se puede.

        Al abrir el puerto el ESP32 se reinicia; cuando termina de arrancar
        llega el evento EVENTO_LISTO.
        """
        puerto = puerto or config.PUERTO_SERIAL
        baudios = baudios or config.BAUDIOS

        self.desconectar()
        try:
            self._serial = serial.serial_for_url(puerto, baudrate=baudios, timeout=0.1)
        except (serial.SerialException, OSError, ValueError):
            self._serial = None
            raise ConnectionError(
                f"No se pudo abrir el puerto {puerto}. Revise que el lector esté "
                "conectado y que el monitor serial de Arduino esté cerrado."
            )

        self.puerto = puerto
        self._detener.clear()
        self._hilo = threading.Thread(target=self._escuchar, daemon=True)
        self._hilo.start()

    def desconectar(self):
        """Detiene el hilo y cierra el puerto."""
        self._detener.set()
        if self._hilo is not None and self._hilo is not threading.current_thread():
            self._hilo.join(timeout=1)
        self._hilo = None
        self._cerrar_puerto()

    def enviar(self, texto):
        """Envía una línea al ESP32. Devuelve True si se pudo enviar."""
        if not self.conectado:
            return False
        try:
            with self._candado:
                self._serial.write((texto + "\n").encode("utf-8"))
            return True
        except (serial.SerialException, OSError):
            return False

    def enviar_mensaje_reposo(self, linea1, linea2=""):
        """Cambia el texto que muestra el LCD mientras espera una tarjeta."""
        return self.enviar(f"MSG:{linea1}|{linea2}")

    def obtener_eventos(self):
        """Devuelve (y saca de la cola) los eventos pendientes como lista de (tipo, dato)."""
        pendientes = []
        while True:
            try:
                pendientes.append(self.eventos.get_nowait())
            except queue.Empty:
                return pendientes

    # ------------------------------------------------------------------
    # Funcionamiento interno
    # ------------------------------------------------------------------

    def _cerrar_puerto(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except (serial.SerialException, OSError):
                pass
        self._serial = None

    def _escuchar(self):
        """Hilo en segundo plano: lee el puerto y convierte cada línea en un evento."""
        puerto = self._serial
        recibido = b""

        while not self._detener.is_set():
            try:
                # Lee lo que haya llegado (o espera como máximo 0.1 s por 1 byte)
                recibido += puerto.read(puerto.in_waiting or 1)
            except (serial.SerialException, OSError, TypeError):
                if not self._detener.is_set():
                    self._cerrar_puerto()
                    self.eventos.put(
                        (EVENTO_DESCONECTADO, "Se perdió la conexión con el lector.")
                    )
                return

            # Puede llegar media línea: solo se procesan las líneas completas.
            while b"\n" in recibido:
                linea, recibido = recibido.split(b"\n", 1)
                self._procesar_linea(linea.decode("utf-8", errors="ignore").strip())

    def _procesar_linea(self, texto):
        if texto.startswith("UID:"):
            uid = texto[4:].strip().upper()
            if uid:
                self.eventos.put((EVENTO_UID, uid))
        elif texto == "READY":
            self.eventos.put((EVENTO_LISTO, None))
        elif texto == "PONG":
            self.eventos.put((EVENTO_PONG, None))
        # Cualquier otro texto (mensajes de arranque del ESP32) se ignora.

"""Ventana principal: barra de conexión con el lector y pestañas."""

import tkinter as tk
from tkinter import messagebox, ttk

import config
from database import clases, conexion
from hardware import lector_serial
from hardware.lector_serial import LectorSerial
from ui.vista_consultas import VistaConsultas
from ui.vista_cursos import VistaCursos
from ui.vista_estudiantes import VistaEstudiantes
from ui.vista_registro import VistaRegistro
from ui.vista_reportes import VistaReportes

INTERVALO_LECTOR_MS = 100   # cada cuánto se revisa si llegó una tarjeta


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de asistencia con RFID")
        self.geometry("1000x660")
        self.minsize(900, 580)

        conexion.crear_tablas()

        self.lector = LectorSerial()
        self._captura_uid = None    # función que espera un UID (asociar tarjeta)

        self._crear_barra_lector()

        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.vista_registro = VistaRegistro(self.pestanas, self)
        self.vista_estudiantes = VistaEstudiantes(self.pestanas, self)
        self.vista_cursos = VistaCursos(self.pestanas, self)
        self.vista_consultas = VistaConsultas(self.pestanas, self)
        self.vista_reportes = VistaReportes(self.pestanas, self)

        self.pestanas.add(self.vista_registro, text="  Registro en vivo  ")
        self.pestanas.add(self.vista_estudiantes, text="  Estudiantes  ")
        self.pestanas.add(self.vista_cursos, text="  Cursos  ")
        self.pestanas.add(self.vista_consultas, text="  Consultas  ")
        self.pestanas.add(self.vista_reportes, text="  Reportes  ")
        self.pestanas.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        self.after(INTERVALO_LECTOR_MS, self._revisar_lector)

    # ------------------------------------------------------------------
    # Barra superior: conexión con el lector
    # ------------------------------------------------------------------

    def _crear_barra_lector(self):
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")

        ttk.Label(barra, text="Lector RFID:").pack(side="left")

        self.combo_puerto = ttk.Combobox(barra, width=12)
        self.combo_puerto.pack(side="left", padx=6)

        ttk.Button(barra, text="Buscar puertos",
                   command=self._cargar_puertos).pack(side="left")

        self.boton_conectar = ttk.Button(barra, text="Conectar",
                                         command=self._conectar_o_desconectar)
        self.boton_conectar.pack(side="left", padx=6)

        self.etiqueta_lector = tk.Label(barra, text="● Lector desconectado (modo simulación)",
                                        fg="#a33")
        self.etiqueta_lector.pack(side="left", padx=10)

        self._cargar_puertos()

    def _cargar_puertos(self):
        puertos = [nombre for nombre, _ in lector_serial.listar_puertos()]
        self.combo_puerto["values"] = puertos
        if not self.combo_puerto.get():
            # Se propone el puerto configurado si existe; si no, el primero.
            if config.PUERTO_SERIAL in puertos or not puertos:
                self.combo_puerto.set(config.PUERTO_SERIAL)
            else:
                self.combo_puerto.set(puertos[0])

    def _conectar_o_desconectar(self):
        if self.lector.conectado:
            self.lector.desconectar()
            self._mostrar_estado_lector("Lector desconectado (modo simulación)", False)
            return

        puerto = self.combo_puerto.get().strip()
        if not puerto:
            messagebox.showwarning("Lector", "Escriba o elija el puerto del lector.")
            return
        try:
            self.lector.conectar(puerto)
        except ConnectionError as error:
            messagebox.showerror("Lector", str(error))
            return
        self._mostrar_estado_lector(f"Conectado a {puerto}", True)
        # Por si el ESP32 no se reinicia al conectar y no envía READY:
        self.after(2500, self.enviar_mensaje_reposo)

    def _mostrar_estado_lector(self, texto, conectado):
        self.etiqueta_lector.config(text="● " + texto,
                                    fg="#1a7f37" if conectado else "#a33")
        self.boton_conectar.config(text="Desconectar" if conectado else "Conectar")

    def enviar_mensaje_reposo(self):
        """Pone en el LCD el curso de la clase abierta (o un aviso si no hay)."""
        clase = clases.clase_abierta()
        if clase is not None:
            self.lector.enviar_mensaje_reposo(clase["curso"][:16], "Pase su tarjeta")
        else:
            self.lector.enviar_mensaje_reposo("Asistencia RFID", "Sin clase activa")

    # ------------------------------------------------------------------
    # Lecturas que llegan del ESP32
    # ------------------------------------------------------------------

    def capturar_uid(self, funcion):
        """La próxima tarjeta leída se entrega a `funcion` en vez de registrarse.

        Se usa para asociar una tarjeta a un estudiante. Con None se cancela.
        """
        self._captura_uid = funcion

    def _revisar_lector(self):
        try:
            for tipo, dato in self.lector.obtener_eventos():
                if tipo == lector_serial.EVENTO_UID:
                    self._al_leer_tarjeta(dato)
                elif tipo == lector_serial.EVENTO_LISTO:
                    self._mostrar_estado_lector(
                        f"Lector listo en {self.lector.puerto}", True)
                    self.enviar_mensaje_reposo()
                elif tipo == lector_serial.EVENTO_DESCONECTADO:
                    self._mostrar_estado_lector(dato, False)
        finally:
            self.after(INTERVALO_LECTOR_MS, self._revisar_lector)

    def _al_leer_tarjeta(self, uid):
        if self._captura_uid is not None:
            # Se está asociando una tarjeta a un estudiante.
            funcion = self._captura_uid
            self._captura_uid = None
            self.lector.enviar(f"OK:Tarjeta leída|{uid}")
            funcion(uid)
        else:
            self.vista_registro.procesar_lectura(uid)

    # ------------------------------------------------------------------
    # Ventana
    # ------------------------------------------------------------------

    def _al_cambiar_pestana(self, _evento=None):
        """Al entrar a una pestaña se recargan sus datos."""
        self._captura_uid = None
        vista = self.pestanas.nametowidget(self.pestanas.select())
        vista.actualizar()

    def _al_cerrar(self):
        self.lector.enviar_mensaje_reposo("Asistencia RFID", "App cerrada")
        self.lector.desconectar()
        self.destroy()

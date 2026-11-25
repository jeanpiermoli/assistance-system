"""Pestaña de registro en vivo.

Aquí se abre y se cierra la clase, se ve quién va llegando (la lista se
actualiza con cada lectura) y se puede registrar en modo simulación,
escribiendo el código sin usar el lector.
"""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import config
from database import asistencias, clases, cursos
from logica import asistencia

COLOR_NEUTRO = "#e9ecef"
COLOR_ACEPTADA = "#b7e4c7"
COLOR_RECHAZADA = "#f5b5b5"


class VistaRegistro(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=10)
        self.app = app
        self.lista_cursos = []
        self.clase = None          # clase que se está mostrando (abierta o recién cerrada)

        self.var_curso = tk.StringVar()
        self.var_clase = tk.StringVar()
        self.var_codigo = tk.StringVar()
        self.var_resumen = tk.StringVar()

        self._crear_controles_clase()
        self._crear_panel_resultado()
        self._crear_simulacion()
        self._crear_tabla()
        self.actualizar()

    # ------------------------------------------------------------------
    # Construcción de la pantalla
    # ------------------------------------------------------------------

    def _crear_controles_clase(self):
        marco = ttk.LabelFrame(self, text="Clase", padding=8)
        marco.pack(fill="x")

        ttk.Label(marco, text="Curso:").pack(side="left")
        self.combo_curso = ttk.Combobox(marco, textvariable=self.var_curso,
                                        state="readonly", width=36)
        self.combo_curso.pack(side="left", padx=6)

        self.boton_abrir = ttk.Button(marco, text="Abrir clase", command=self._abrir_clase)
        self.boton_abrir.pack(side="left", padx=2)
        self.boton_cerrar = ttk.Button(marco, text="Cerrar clase", command=self._cerrar_clase)
        self.boton_cerrar.pack(side="left", padx=2)

        ttk.Label(marco, textvariable=self.var_clase).pack(side="left", padx=12)

    def _crear_panel_resultado(self):
        self.panel = tk.Label(self, text="", font=("Segoe UI", 20, "bold"),
                              bg=COLOR_NEUTRO, fg="#222", height=2)
        self.panel.pack(fill="x", pady=8)

    def _crear_simulacion(self):
        marco = ttk.LabelFrame(self, text="Modo simulación (sin lector)", padding=8)
        marco.pack(fill="x")

        ttk.Label(marco, text="Código de tarjeta o código estudiantil:").pack(side="left")
        self.entrada_codigo = ttk.Entry(marco, textvariable=self.var_codigo, width=22)
        self.entrada_codigo.pack(side="left", padx=6)
        self.entrada_codigo.bind("<Return>", lambda _e: self._registrar_simulado())
        ttk.Button(marco, text="Registrar",
                   command=self._registrar_simulado).pack(side="left")

    def _crear_tabla(self):
        ttk.Label(self, textvariable=self.var_resumen,
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 4))

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)

        columnas = ("hora", "codigo", "nombre", "estado")
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings")
        self.tabla.heading("hora", text="Hora")
        self.tabla.heading("codigo", text="Código")
        self.tabla.heading("nombre", text="Estudiante")
        self.tabla.heading("estado", text="Estado")
        self.tabla.column("hora", width=90, anchor="center")
        self.tabla.column("codigo", width=110, anchor="center")
        self.tabla.column("nombre", width=320)
        self.tabla.column("estado", width=110, anchor="center")

        self.tabla.tag_configure(config.A_TIEMPO, background="#d8f3dc")
        self.tabla.tag_configure(config.TARDE, background="#fff3bf")
        self.tabla.tag_configure(config.AUSENTE, background="#ffd6d6")

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")

    # ------------------------------------------------------------------
    # Actualización de la pantalla
    # ------------------------------------------------------------------

    def actualizar(self):
        """Recarga los cursos, la clase abierta y la lista de asistencia."""
        self.lista_cursos = cursos.listar()
        nombres = [f"{c['nombre']}  ({c['dia']} {c['hora_inicio']})"
                   for c in self.lista_cursos]
        self.combo_curso["values"] = nombres
        if self.var_curso.get() not in nombres:
            self.var_curso.set(nombres[0] if nombres else "")

        abierta = clases.clase_abierta()
        if abierta is not None:
            self.clase = abierta
        elif self.clase is not None:
            self.clase = clases.obtener(self.clase["id"])   # pudo ser eliminada

        hay_abierta = abierta is not None
        self.boton_abrir.config(state="disabled" if hay_abierta else "normal")
        self.boton_cerrar.config(state="normal" if hay_abierta else "disabled")
        self.combo_curso.config(state="disabled" if hay_abierta else "readonly")

        if self.clase is None:
            self.var_clase.set("No hay clase abierta.")
            self._mostrar_panel("Abra una clase para comenzar", COLOR_NEUTRO)
        elif hay_abierta:
            self.var_clase.set(
                f"ABIERTA: {self.clase['curso']} · {self.clase['fecha']} · "
                f"inicio {self.clase['hora_inicio']} · "
                f"tolerancia {self.clase['tolerancia_min']} min")
            if not self.panel.cget("text") or self.panel.cget("bg") == COLOR_NEUTRO:
                self._mostrar_panel("Esperando tarjetas...", COLOR_NEUTRO)
        else:
            self.var_clase.set(
                f"CERRADA: {self.clase['curso']} · {self.clase['fecha']}")

        self._recargar_tabla()

    def _recargar_tabla(self):
        self.tabla.delete(*self.tabla.get_children())
        if self.clase is None:
            self.var_resumen.set("")
            return

        for fila in asistencias.listar_por_clase(self.clase["id"]):
            self.tabla.insert("", "end", tags=(fila["estado"],),
                              values=(fila["hora"] or "—", fila["codigo"],
                                      fila["nombre"], fila["estado"].capitalize()))

        r = asistencia.resumen_clase(self.clase["id"])
        self.var_resumen.set(
            f"A tiempo: {r[config.A_TIEMPO]}     Tarde: {r[config.TARDE]}     "
            f"Ausentes: {r[config.AUSENTE]}     Sin registrar: {r['pendientes']}")

    def _mostrar_panel(self, texto, color):
        self.panel.config(text=texto, bg=color)

    # ------------------------------------------------------------------
    # Lecturas (del lector real o del modo simulación)
    # ------------------------------------------------------------------

    def procesar_lectura(self, codigo, simulacion=False):
        """Registra una lectura, responde al ESP32 y actualiza la pantalla."""
        resultado = asistencia.registrar_lectura(
            codigo, permitir_codigo_estudiantil=simulacion)

        # El ESP32 enciende el LED, suena y muestra el texto en el LCD.
        self.app.lector.enviar(resultado.comando_serial())

        self._mostrar_panel(resultado.mensaje,
                            COLOR_ACEPTADA if resultado.aceptada else COLOR_RECHAZADA)
        if resultado.aceptada:
            self._recargar_tabla()
        return resultado

    def _registrar_simulado(self):
        codigo = self.var_codigo.get().strip()
        if not codigo:
            return
        self.procesar_lectura(codigo, simulacion=True)
        self.var_codigo.set("")
        self.entrada_codigo.focus_set()

    # ------------------------------------------------------------------
    # Abrir y cerrar la clase
    # ------------------------------------------------------------------

    def _abrir_clase(self):
        indice = self.combo_curso.current()
        if indice < 0:
            messagebox.showinfo("Abrir clase",
                                "Primero cree un curso en la pestaña «Cursos».")
            return
        curso = self.lista_cursos[indice]

        hoy = config.DIAS[datetime.now().weekday()]
        if curso["dia"] != hoy:
            if not messagebox.askyesno(
                    "Abrir clase",
                    f"Este curso es de los {curso['dia'].lower()} y hoy es "
                    f"{hoy.lower()}.\n\n¿Abrir la clase de todos modos?"):
                return
        try:
            self.clase = asistencia.abrir_clase(curso["id"])
        except ValueError as error:
            messagebox.showerror("Abrir clase", str(error))
            return

        self._mostrar_panel("Esperando tarjetas...", COLOR_NEUTRO)
        self.actualizar()
        self.app.enviar_mensaje_reposo()

    def _cerrar_clase(self):
        abierta = clases.clase_abierta()
        if abierta is None:
            return
        pendientes = asistencia.resumen_clase(abierta["id"])["pendientes"]
        if not messagebox.askyesno(
                "Cerrar clase",
                f"¿Cerrar la clase de {abierta['curso']}?\n\n"
                f"{pendientes} estudiante(s) sin registrar quedarán como AUSENTES."):
            return

        ausentes = asistencia.cerrar_clase(abierta["id"])
        self._mostrar_panel(f"Clase cerrada · {ausentes} ausente(s)", COLOR_NEUTRO)
        self.actualizar()
        self.app.enviar_mensaje_reposo()

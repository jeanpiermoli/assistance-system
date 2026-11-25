"""Pestaña de consultas: asistencia por estudiante, por curso y por fecha, con exportación a Excel."""

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import config
from database import asistencias, cursos, estudiantes
from logica import exportar

TODOS = "(Todos)"


class VistaConsultas(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=10)
        self.app = app
        self.lista_estudiantes = []
        self.lista_cursos = []
        self.filas = []            # resultado de la última consulta

        self.var_estudiante = tk.StringVar(value=TODOS)
        self.var_curso = tk.StringVar(value=TODOS)
        self.var_desde = tk.StringVar()
        self.var_hasta = tk.StringVar()
        self.var_total = tk.StringVar()

        self._crear_filtros()
        self._crear_tabla()
        self.actualizar()

    def _crear_filtros(self):
        marco = ttk.LabelFrame(self, text="Filtros", padding=8)
        marco.pack(fill="x")

        ttk.Label(marco, text="Estudiante:").grid(row=0, column=0, sticky="w")
        self.combo_estudiante = ttk.Combobox(marco, textvariable=self.var_estudiante,
                                             state="readonly", width=34)
        self.combo_estudiante.grid(row=0, column=1, padx=6, pady=2)

        ttk.Label(marco, text="Curso:").grid(row=1, column=0, sticky="w")
        self.combo_curso = ttk.Combobox(marco, textvariable=self.var_curso,
                                        state="readonly", width=34)
        self.combo_curso.grid(row=1, column=1, padx=6, pady=2)

        ttk.Label(marco, text="Desde (AAAA-MM-DD):").grid(row=0, column=2, sticky="w", padx=(16, 0))
        ttk.Entry(marco, textvariable=self.var_desde, width=14).grid(row=0, column=3, padx=6)

        ttk.Label(marco, text="Hasta (AAAA-MM-DD):").grid(row=1, column=2, sticky="w", padx=(16, 0))
        ttk.Entry(marco, textvariable=self.var_hasta, width=14).grid(row=1, column=3, padx=6)

        ttk.Button(marco, text="Consultar", command=self._consultar).grid(
            row=0, column=4, padx=10, sticky="we")
        ttk.Button(marco, text="Quitar filtros", command=self._quitar_filtros).grid(
            row=1, column=4, padx=10, sticky="we")
        ttk.Button(marco, text="Exportar a Excel", command=self._exportar).grid(
            row=0, column=5, rowspan=2, padx=6, sticky="ns")

    def _crear_tabla(self):
        ttk.Label(self, textvariable=self.var_total,
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 4))

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)

        columnas = ("fecha", "curso", "codigo", "estudiante", "hora", "estado")
        titulos = ("Fecha", "Curso", "Código", "Estudiante", "Hora", "Estado")
        anchos = (95, 220, 100, 260, 85, 95)

        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings")
        for columna, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(columna, text=titulo)
            centrar = columna not in ("curso", "estudiante")
            self.tabla.column(columna, width=ancho, anchor="center" if centrar else "w")

        self.tabla.tag_configure(config.A_TIEMPO, background="#d8f3dc")
        self.tabla.tag_configure(config.TARDE, background="#fff3bf")
        self.tabla.tag_configure(config.AUSENTE, background="#ffd6d6")

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def actualizar(self):
        """Recarga las listas de filtros y repite la consulta."""
        self.lista_estudiantes = estudiantes.listar()
        self.lista_cursos = cursos.listar()

        nombres = [TODOS] + [f"{e['nombre']} ({e['codigo']})" for e in self.lista_estudiantes]
        self.combo_estudiante["values"] = nombres
        if self.var_estudiante.get() not in nombres:
            self.var_estudiante.set(TODOS)

        nombres = [TODOS] + [c["nombre"] for c in self.lista_cursos]
        self.combo_curso["values"] = nombres
        if self.var_curso.get() not in nombres:
            self.var_curso.set(TODOS)

        self._consultar(avisar=False)

    def _leer_fecha(self, texto, nombre):
        """Valida una fecha escrita. Devuelve None si el campo está vacío."""
        texto = texto.strip()
        if not texto:
            return None
        try:
            return datetime.strptime(texto, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(f"La fecha «{nombre}» debe tener el formato AAAA-MM-DD "
                             "(ejemplo: 2026-11-24).")

    def _consultar(self, avisar=True):
        try:
            desde = self._leer_fecha(self.var_desde.get(), "Desde")
            hasta = self._leer_fecha(self.var_hasta.get(), "Hasta")
        except ValueError as error:
            if avisar:
                messagebox.showerror("Consultas", str(error))
            return

        # La posición 0 de cada lista desplegable es "(Todos)".
        i = self.combo_estudiante.current()
        estudiante_id = self.lista_estudiantes[i - 1]["id"] if i > 0 else None
        i = self.combo_curso.current()
        curso_id = self.lista_cursos[i - 1]["id"] if i > 0 else None

        self.filas = asistencias.consultar_asistencias(estudiante_id, curso_id, desde, hasta)

        self.tabla.delete(*self.tabla.get_children())
        for f in self.filas:
            self.tabla.insert("", "end", tags=(f["estado"],),
                              values=(f["fecha"], f["curso"], f["codigo"], f["estudiante"],
                                      f["hora"] or "—", f["estado"].capitalize()))

        conteo = {config.A_TIEMPO: 0, config.TARDE: 0, config.AUSENTE: 0}
        for f in self.filas:
            conteo[f["estado"]] += 1
        self.var_total.set(
            f"{len(self.filas)} registros     A tiempo: {conteo[config.A_TIEMPO]}     "
            f"Tarde: {conteo[config.TARDE]}     Ausencias: {conteo[config.AUSENTE]}")

    def _quitar_filtros(self):
        self.var_estudiante.set(TODOS)
        self.var_curso.set(TODOS)
        self.var_desde.set("")
        self.var_hasta.set("")
        self._consultar()

    def _exportar(self):
        if not self.filas:
            messagebox.showinfo("Exportar a Excel", "No hay registros para exportar.")
            return

        os.makedirs(config.CARPETA_EXPORTES, exist_ok=True)
        nombre = "asistencia_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".xlsx"
        ruta = filedialog.asksaveasfilename(
            title="Exportar a Excel", initialdir=config.CARPETA_EXPORTES,
            initialfile=nombre, defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        try:
            ruta = exportar.exportar_asistencias(self.filas, ruta)
        except ValueError as error:
            messagebox.showerror("Exportar a Excel", str(error))
            return
        messagebox.showinfo("Exportar a Excel",
                            f"Se exportaron {len(self.filas)} registros a:\n{ruta}")

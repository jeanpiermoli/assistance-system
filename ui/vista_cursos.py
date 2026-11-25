"""Pestaña de cursos: nombre, día, hora de inicio y tolerancia de llegada."""

import tkinter as tk
from tkinter import messagebox, ttk

import config
from database import cursos


class VistaCursos(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=10)
        self.app = app
        self.id_seleccionado = None

        self.var_nombre = tk.StringVar()
        self.var_dia = tk.StringVar(value=config.DIAS[0])
        self.var_hora = tk.StringVar(value="07:00")
        self.var_tolerancia = tk.StringVar(value="10")

        self._crear_formulario()
        self._crear_tabla()
        self.actualizar()

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Datos del curso", padding=10)
        marco.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(marco, text="Nombre del curso:").grid(row=0, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.var_nombre, width=28).grid(
            row=1, column=0, sticky="we", pady=(0, 8))

        ttk.Label(marco, text="Día:").grid(row=2, column=0, sticky="w")
        ttk.Combobox(marco, textvariable=self.var_dia, values=config.DIAS,
                     state="readonly").grid(row=3, column=0, sticky="we", pady=(0, 8))

        ttk.Label(marco, text="Hora de inicio (HH:MM, 24 horas):").grid(
            row=4, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.var_hora).grid(
            row=5, column=0, sticky="we", pady=(0, 8))

        ttk.Label(marco, text="Tolerancia de llegada (minutos):").grid(
            row=6, column=0, sticky="w")
        ttk.Spinbox(marco, textvariable=self.var_tolerancia, from_=0, to=120).grid(
            row=7, column=0, sticky="we", pady=(0, 12))

        ttk.Button(marco, text="Guardar nuevo", command=self._guardar_nuevo).grid(
            row=8, column=0, sticky="we", pady=2)
        ttk.Button(marco, text="Guardar cambios", command=self._guardar_cambios).grid(
            row=9, column=0, sticky="we", pady=2)
        ttk.Button(marco, text="Eliminar", command=self._eliminar).grid(
            row=10, column=0, sticky="we", pady=2)
        ttk.Button(marco, text="Limpiar formulario", command=self._limpiar).grid(
            row=11, column=0, sticky="we", pady=2)

    def _crear_tabla(self):
        marco = ttk.Frame(self)
        marco.pack(side="left", fill="both", expand=True)

        columnas = ("nombre", "dia", "hora", "tolerancia")
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings")
        self.tabla.heading("nombre", text="Curso")
        self.tabla.heading("dia", text="Día")
        self.tabla.heading("hora", text="Hora de inicio")
        self.tabla.heading("tolerancia", text="Tolerancia")
        self.tabla.column("nombre", width=280)
        self.tabla.column("dia", width=100, anchor="center")
        self.tabla.column("hora", width=100, anchor="center")
        self.tabla.column("tolerancia", width=100, anchor="center")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)

    def actualizar(self):
        """Recarga la tabla con los cursos de la base de datos."""
        self.tabla.delete(*self.tabla.get_children())
        for c in cursos.listar():
            self.tabla.insert("", "end", iid=str(c["id"]),
                              values=(c["nombre"], c["dia"], c["hora_inicio"],
                                      f"{c['tolerancia_min']} min"))

    def _al_seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        curso = cursos.obtener(int(seleccion[0]))
        if curso is None:
            return
        self.id_seleccionado = curso["id"]
        self.var_nombre.set(curso["nombre"])
        self.var_dia.set(curso["dia"])
        self.var_hora.set(curso["hora_inicio"])
        self.var_tolerancia.set(str(curso["tolerancia_min"]))

    def _limpiar(self):
        self.id_seleccionado = None
        self.var_nombre.set("")
        self.var_dia.set(config.DIAS[0])
        self.var_hora.set("07:00")
        self.var_tolerancia.set("10")
        self.tabla.selection_remove(self.tabla.selection())

    def _datos(self):
        return (self.var_nombre.get(), self.var_dia.get(),
                self.var_hora.get(), self.var_tolerancia.get())

    def _guardar_nuevo(self):
        try:
            cursos.crear(*self._datos())
        except ValueError as error:
            messagebox.showerror("Cursos", str(error))
            return
        self._limpiar()
        self.actualizar()

    def _guardar_cambios(self):
        if self.id_seleccionado is None:
            messagebox.showinfo("Cursos", "Primero seleccione un curso de la lista.")
            return
        try:
            cursos.actualizar(self.id_seleccionado, *self._datos())
        except ValueError as error:
            messagebox.showerror("Cursos", str(error))
            return
        self._limpiar()
        self.actualizar()

    def _eliminar(self):
        if self.id_seleccionado is None:
            messagebox.showinfo("Cursos", "Primero seleccione un curso de la lista.")
            return
        if not messagebox.askyesno(
                "Eliminar curso",
                f"¿Eliminar el curso {self.var_nombre.get()}?\n\n"
                "También se eliminarán sus clases y asistencias. No se puede deshacer."):
            return
        cursos.eliminar(self.id_seleccionado)
        self._limpiar()
        self.actualizar()
        self.app.enviar_mensaje_reposo()

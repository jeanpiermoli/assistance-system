"""Pestaña de estudiantes: registrar, editar, eliminar y asociar la tarjeta."""

import tkinter as tk
from tkinter import messagebox, ttk

from database import estudiantes


class VistaEstudiantes(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=10)
        self.app = app
        self.id_seleccionado = None

        self.var_codigo = tk.StringVar()
        self.var_nombre = tk.StringVar()
        self.var_uid = tk.StringVar()
        self.var_aviso = tk.StringVar()

        self._crear_formulario()
        self._crear_tabla()
        self.actualizar()

    # ------------------------------------------------------------------
    # Construcción de la pantalla
    # ------------------------------------------------------------------

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Datos del estudiante", padding=10)
        marco.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(marco, text="Código estudiantil:").grid(row=0, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.var_codigo, width=28).grid(
            row=1, column=0, columnspan=2, sticky="we", pady=(0, 8))

        ttk.Label(marco, text="Nombre completo:").grid(row=2, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.var_nombre, width=28).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(0, 8))

        ttk.Label(marco, text="Código de la tarjeta (UID):").grid(row=4, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.var_uid, width=18).grid(
            row=5, column=0, sticky="we", pady=(0, 4))
        ttk.Button(marco, text="Leer tarjeta", command=self._leer_tarjeta).grid(
            row=5, column=1, padx=(6, 0), pady=(0, 4))

        ttk.Label(marco, textvariable=self.var_aviso, foreground="#0a58ca",
                  wraplength=230).grid(row=6, column=0, columnspan=2, sticky="w",
                                       pady=(0, 10))

        ttk.Button(marco, text="Guardar nuevo", command=self._guardar_nuevo).grid(
            row=7, column=0, columnspan=2, sticky="we", pady=2)
        ttk.Button(marco, text="Guardar cambios", command=self._guardar_cambios).grid(
            row=8, column=0, columnspan=2, sticky="we", pady=2)
        ttk.Button(marco, text="Eliminar", command=self._eliminar).grid(
            row=9, column=0, columnspan=2, sticky="we", pady=2)
        ttk.Button(marco, text="Limpiar formulario", command=self._limpiar).grid(
            row=10, column=0, columnspan=2, sticky="we", pady=2)

    def _crear_tabla(self):
        marco = ttk.Frame(self)
        marco.pack(side="left", fill="both", expand=True)

        self.var_total = tk.StringVar()
        ttk.Label(marco, textvariable=self.var_total).pack(anchor="w", pady=(0, 4))

        columnas = ("codigo", "nombre", "uid")
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings")
        self.tabla.heading("codigo", text="Código")
        self.tabla.heading("nombre", text="Nombre")
        self.tabla.heading("uid", text="Tarjeta (UID)")
        self.tabla.column("codigo", width=110, anchor="center")
        self.tabla.column("nombre", width=280)
        self.tabla.column("uid", width=130, anchor="center")

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")

        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def actualizar(self):
        """Recarga la tabla con los estudiantes de la base de datos."""
        self.tabla.delete(*self.tabla.get_children())
        lista = estudiantes.listar()
        for e in lista:
            self.tabla.insert("", "end", iid=str(e["id"]),
                              values=(e["codigo"], e["nombre"],
                                      e["uid_tarjeta"] or "(sin tarjeta)"))
        sin_tarjeta = sum(1 for e in lista if not e["uid_tarjeta"])
        self.var_total.set(f"{len(lista)} estudiantes registrados"
                           + (f"  ·  {sin_tarjeta} sin tarjeta" if sin_tarjeta else ""))

    def _al_seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        estudiante = estudiantes.obtener(int(seleccion[0]))
        if estudiante is None:
            return
        self.id_seleccionado = estudiante["id"]
        self.var_codigo.set(estudiante["codigo"])
        self.var_nombre.set(estudiante["nombre"])
        self.var_uid.set(estudiante["uid_tarjeta"] or "")
        self.var_aviso.set("")

    def _limpiar(self):
        self.id_seleccionado = None
        self.var_codigo.set("")
        self.var_nombre.set("")
        self.var_uid.set("")
        self.var_aviso.set("")
        self.app.capturar_uid(None)
        self.tabla.selection_remove(self.tabla.selection())

    def _leer_tarjeta(self):
        """Espera a que se pase una tarjeta por el lector y escribe su UID."""
        if not self.app.lector.conectado:
            messagebox.showinfo(
                "Leer tarjeta",
                "El lector no está conectado.\n\nConéctelo con el botón «Conectar» "
                "o escriba el código de la tarjeta a mano.")
            return
        self.var_aviso.set("Pase la tarjeta por el lector...")
        self.app.capturar_uid(self._tarjeta_leida)

    def _tarjeta_leida(self, uid):
        self.var_uid.set(uid)
        duenio = estudiantes.buscar_por_uid(uid)
        if duenio is not None and duenio["id"] != self.id_seleccionado:
            self.var_aviso.set(f"Atención: esa tarjeta ya es de {duenio['nombre']}.")
        else:
            self.var_aviso.set("Tarjeta leída. Ahora guarde los datos.")

    def _guardar_nuevo(self):
        try:
            estudiantes.crear(self.var_codigo.get(), self.var_nombre.get(),
                              self.var_uid.get())
        except ValueError as error:
            messagebox.showerror("Estudiantes", str(error))
            return
        self._limpiar()
        self.actualizar()

    def _guardar_cambios(self):
        if self.id_seleccionado is None:
            messagebox.showinfo("Estudiantes", "Primero seleccione un estudiante de la lista.")
            return
        try:
            estudiantes.actualizar(self.id_seleccionado, self.var_codigo.get(),
                                   self.var_nombre.get(), self.var_uid.get())
        except ValueError as error:
            messagebox.showerror("Estudiantes", str(error))
            return
        self._limpiar()
        self.actualizar()

    def _eliminar(self):
        if self.id_seleccionado is None:
            messagebox.showinfo("Estudiantes", "Primero seleccione un estudiante de la lista.")
            return
        if not messagebox.askyesno(
                "Eliminar estudiante",
                f"¿Eliminar a {self.var_nombre.get()}?\n\n"
                "También se eliminarán todas sus asistencias. No se puede deshacer."):
            return
        estudiantes.eliminar(self.id_seleccionado)
        self._limpiar()
        self.actualizar()

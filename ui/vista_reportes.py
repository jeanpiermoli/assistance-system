"""Pestaña de reportes: dos gráficas y la alerta de estudiantes con muchas fallas."""

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

import config
from database import cursos
from logica import reportes

TODOS = "(Todos los cursos)"
COLOR_BARRAS = "#2f6fb5"
COLOR_TEXTO = "#333333"
COLOR_SUAVE = "#777777"
COLOR_REJILLA = "#e3e3e3"


def _estilo_ejes(ejes):
    """Deja los ejes discretos para que lo que resalte sean las barras."""
    for lado in ("top", "right"):
        ejes.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ejes.spines[lado].set_color(COLOR_REJILLA)
    ejes.tick_params(colors=COLOR_SUAVE, labelsize=8, length=0)
    ejes.set_axisbelow(True)


class VistaReportes(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=10)
        self.app = app
        self.lista_cursos = []

        self.var_curso = tk.StringVar(value=TODOS)
        self.var_alerta = tk.StringVar()

        self._crear_filtro()
        self._crear_alertas()
        self._crear_graficas()
        self.actualizar()

    # ------------------------------------------------------------------

    def _crear_filtro(self):
        marco = ttk.Frame(self)
        marco.pack(fill="x")
        ttk.Label(marco, text="Curso:").pack(side="left")
        self.combo_curso = ttk.Combobox(marco, textvariable=self.var_curso,
                                        state="readonly", width=36)
        self.combo_curso.pack(side="left", padx=6)
        self.combo_curso.bind("<<ComboboxSelected>>", lambda _e: self._dibujar())
        ttk.Button(marco, text="Actualizar", command=self.actualizar).pack(side="left")

    def _crear_alertas(self):
        marco = ttk.LabelFrame(
            self, text=f"Alerta: estudiantes con más de {config.UMBRAL_FALLAS} fallas",
            padding=8)
        marco.pack(fill="x", pady=8)
        self.etiqueta_alerta = tk.Label(marco, textvariable=self.var_alerta,
                                        justify="left", anchor="w", wraplength=920)
        self.etiqueta_alerta.pack(fill="x")

    def _crear_graficas(self):
        self.figura = Figure(figsize=(10, 4.4), dpi=100, facecolor="white")
        self.ejes_porcentaje = self.figura.add_subplot(1, 2, 1)
        self.ejes_tardes = self.figura.add_subplot(1, 2, 2)

        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------

    def actualizar(self):
        """Recarga la lista de cursos y vuelve a dibujar los reportes."""
        self.lista_cursos = cursos.listar()
        nombres = [TODOS] + [c["nombre"] for c in self.lista_cursos]
        self.combo_curso["values"] = nombres
        if self.var_curso.get() not in nombres:
            self.var_curso.set(TODOS)
        self._dibujar()

    def _dibujar(self):
        i = self.combo_curso.current()
        curso_id = self.lista_cursos[i - 1]["id"] if i > 0 else None
        datos = reportes.cargar_datos(curso_id)

        self._mostrar_alertas(reportes.estudiantes_en_alerta(datos))
        self._graficar_porcentaje(reportes.resumen_por_estudiante(datos),
                                  reportes.estudiantes_en_alerta(datos))
        self._graficar_tardes(reportes.tardes_por_fecha(datos))

        self.figura.tight_layout(pad=1.6)
        self.lienzo.draw_idle()

    def _mostrar_alertas(self, alerta):
        if alerta.empty:
            self.var_alerta.set("Ningún estudiante supera el límite de fallas.")
            self.etiqueta_alerta.config(fg="#1a7f37")
            return
        nombres = [f"⚠ {fila.estudiante} ({fila.ausencias} fallas)"
                   for fila in alerta.itertuples()]
        self.var_alerta.set("     ".join(nombres))
        self.etiqueta_alerta.config(fg="#b3261e")

    def _sin_datos(self, ejes, titulo):
        ejes.clear()
        ejes.set_title(titulo, fontsize=10, color=COLOR_TEXTO, loc="left")
        ejes.text(0.5, 0.5, "Todavía no hay clases cerradas", ha="center", va="center",
                  color=COLOR_SUAVE, transform=ejes.transAxes)
        ejes.set_xticks([])
        ejes.set_yticks([])
        for lado in ejes.spines.values():
            lado.set_visible(False)

    def _graficar_porcentaje(self, resumen, alerta):
        """Gráfica 1: porcentaje de asistencia por estudiante (barras horizontales)."""
        ejes = self.ejes_porcentaje
        titulo = "Porcentaje de asistencia por estudiante"
        if resumen.empty:
            self._sin_datos(ejes, titulo)
            return

        ejes.clear()
        resumen = resumen.iloc[::-1]          # el mayor porcentaje queda arriba
        en_alerta = set(alerta["codigo"])
        nombres = [("⚠ " if fila.codigo in en_alerta else "") + fila.estudiante
                   for fila in resumen.itertuples()]

        barras = ejes.barh(nombres, resumen["porcentaje"], color=COLOR_BARRAS, height=0.62)
        ejes.bar_label(barras, labels=[f"{p:.0f}%" for p in resumen["porcentaje"]],
                       padding=3, fontsize=7, color=COLOR_TEXTO)

        ejes.set_title(titulo, fontsize=10, color=COLOR_TEXTO, loc="left")
        ejes.set_xlim(0, 112)
        ejes.set_xticks([0, 25, 50, 75, 100])
        ejes.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ejes.grid(axis="x", color=COLOR_REJILLA, linewidth=0.8)
        _estilo_ejes(ejes)
        ejes.tick_params(axis="y", labelsize=7, colors=COLOR_TEXTO)
        ejes.margins(y=0.02)

    def _graficar_tardes(self, tardes):
        """Gráfica 2: llegadas tarde por fecha (barras verticales)."""
        ejes = self.ejes_tardes
        titulo = "Llegadas tarde por fecha"
        if tardes.empty:
            self._sin_datos(ejes, titulo)
            return

        ejes.clear()
        # Fechas como "24/11" para que quepan en el eje.
        etiquetas = [f"{f[8:10]}/{f[5:7]}" for f in tardes["fecha"]]
        posiciones = range(len(etiquetas))

        barras = ejes.bar(posiciones, tardes["tardes"], color=COLOR_BARRAS, width=0.6)
        ejes.bar_label(barras, padding=2, fontsize=8, color=COLOR_TEXTO)

        ejes.set_title(titulo, fontsize=10, color=COLOR_TEXTO, loc="left")
        ejes.set_xticks(list(posiciones))
        ejes.set_xticklabels(etiquetas, rotation=45 if len(etiquetas) > 10 else 0)
        ejes.set_ylabel("Estudiantes que llegaron tarde", fontsize=8, color=COLOR_SUAVE)
        ejes.set_ylim(0, max(tardes["tardes"].max(), 1) * 1.18)
        ejes.yaxis.set_major_locator(MaxNLocator(integer=True))
        ejes.grid(axis="y", color=COLOR_REJILLA, linewidth=0.8)
        _estilo_ejes(ejes)

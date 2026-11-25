"""Exportación de asistencias a Excel."""

import os

import pandas as pd

COLUMNAS = {
    "fecha": "Fecha",
    "curso": "Curso",
    "codigo": "Código",
    "estudiante": "Estudiante",
    "hora": "Hora",
    "estado": "Estado",
}


def exportar_asistencias(filas, ruta):
    """Guarda en un archivo .xlsx las filas de una consulta de asistencias.

    filas: lista de diccionarios de asistencias.consultar_asistencias().
    ruta:  archivo de destino. Devuelve la ruta final (siempre termina en .xlsx).
    """
    if not filas:
        raise ValueError("No hay asistencias para exportar.")
    if not ruta.lower().endswith(".xlsx"):
        ruta += ".xlsx"

    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    tabla = pd.DataFrame(filas)[list(COLUMNAS)].rename(columns=COLUMNAS)
    tabla["Hora"] = tabla["Hora"].fillna("")
    tabla["Estado"] = tabla["Estado"].str.capitalize()

    try:
        with pd.ExcelWriter(ruta, engine="openpyxl") as escritor:
            tabla.to_excel(escritor, sheet_name="Asistencias", index=False)

            # Ajusta el ancho de cada columna a su contenido.
            hoja = escritor.sheets["Asistencias"]
            for numero, columna in enumerate(tabla.columns, start=1):
                ancho = max(len(str(columna)),
                            tabla[columna].astype(str).str.len().max())
                letra = hoja.cell(row=1, column=numero).column_letter
                hoja.column_dimensions[letra].width = ancho + 3
            hoja.freeze_panes = "A2"
    except PermissionError:
        raise ValueError(
            "No se pudo guardar el archivo. Si está abierto en Excel, ciérrelo "
            "e intente de nuevo.")
    return ruta

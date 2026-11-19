"""Conserva el Excel de incidencia y añade la tabla mensual de inhumación.

Uso:
    python combinar_excel_reporte.py --excel-incidencia ENTRADA.xlsx \
        --datos-inhumacion DATOS.json --salida SALIDA.xlsx
"""

import argparse
from datetime import date
import json
from pathlib import Path
import re
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


HOJA = "Sitios de inhumación"
HOJAS_ANTERIORES = {"Inhumación mensual", "Inhumación detalle"}
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()
PATRON_MES = re.compile(r"^(?:" + "|".join(MESES) + r")-\d{2}$")
ENCABEZADOS = (
    "Mes de inicio de procesamiento",
    "Número de sitios registrados",
    "Total preliminar de víctimas localizadas",
)


def leer_datos(ruta: Path) -> list[tuple[str, int, int]]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    corte = date.fromisoformat(datos["corte"])
    if corte.day != 1:
        raise ValueError("El corte debe ser el primer día del mes.")
    mensual = datos["mensual"]
    if not isinstance(mensual, list) or not mensual:
        raise ValueError("Faltan las filas mensuales de inhumación.")
    filas = []
    for fila in mensual:
        if not isinstance(fila, list) or len(fila) != 3:
            raise ValueError("Cada fila de inhumación debe tener tres columnas.")
        mes, sitios, victimas = fila
        if not isinstance(mes, str) or not PATRON_MES.fullmatch(mes):
            raise ValueError(f"Mes de inhumación no válido: {mes!r}.")
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (sitios, victimas)):
            raise ValueError(f"Las cifras de {mes} deben ser enteros no negativos.")
        filas.append((mes, sitios, victimas))
    if len({fila[0] for fila in filas}) != len(filas):
        raise ValueError("Hay meses repetidos en la tabla de inhumación.")
    return filas


def combinar(entrada: Path, datos: Path, salida: Path) -> None:
    if not entrada.is_file() or entrada.suffix.lower() != ".xlsx":
        raise ValueError(f"No existe el Excel de incidencia: {entrada}")
    if salida.exists():
        raise FileExistsError(f"Ya existe el Excel de salida: {salida}")
    filas = leer_datos(datos)
    with ZipFile(entrada) as archivo:
        componentes = archivo.namelist()
    no_compatibles = (
        "xl/drawings/", "xl/charts/", "xl/pivotTables/", "xl/externalLinks/",
        "xl/embeddings/", "xl/vbaProject.bin",
    )
    if any(nombre.startswith(no_compatibles) for nombre in componentes):
        raise ValueError(
            "El Excel de incidencia contiene gráficos, objetos, tablas dinámicas, "
            "vínculos externos o macros. Revisa ese archivo antes de combinarlo con openpyxl."
        )
    libro = load_workbook(entrada, read_only=False, data_only=False, keep_links=True)
    repetidas = ({HOJA} | HOJAS_ANTERIORES) & set(libro.sheetnames)
    if repetidas:
        raise ValueError(f"El Excel de incidencia ya contiene estas hojas: {sorted(repetidas)}")
    if any(celda.data_type == "f" for hoja_original in libro for fila in hoja_original for celda in fila):
        raise ValueError(
            "El Excel de incidencia contiene fórmulas. Revisa su recálculo antes "
            "de combinarlo, porque openpyxl no conserva los resultados en caché."
        )

    hoja = libro.create_sheet(HOJA)
    hoja.sheet_view.showGridLines = False
    hoja.merge_cells("A1:C2")
    titulo = hoja["A1"]
    titulo.value = HOJA
    titulo.font = Font(name="Arial", size=14, bold=True, color="111111")
    titulo.alignment = Alignment(vertical="center")
    hoja.row_dimensions[1].height = 30
    hoja.row_dimensions[2].height = 30

    fondo_encabezado = PatternFill("solid", fgColor="303040")
    fondo_alterno = PatternFill("solid", fgColor="F3F3F5")
    for columna, texto in enumerate(ENCABEZADOS, start=1):
        celda = hoja.cell(4, columna, texto)
        celda.fill = fondo_encabezado
        celda.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hoja.row_dimensions[4].height = 54

    for numero, (mes, sitios, victimas) in enumerate(filas, start=5):
        for columna, valor in enumerate((mes, sitios, victimas), start=1):
            celda = hoja.cell(numero, columna, valor)
            celda.font = Font(name="Arial", size=10, color="111111")
            if columna > 1:
                celda.number_format = "#,##0"
            if numero % 2:
                celda.fill = fondo_alterno
    hoja.column_dimensions["A"].width = 24
    hoja.column_dimensions["B"].width = 30
    hoja.column_dimensions["C"].width = 34
    hoja.freeze_panes = "A5"

    salida.parent.mkdir(parents=True, exist_ok=True)
    libro.save(salida)
    libro.close()
    print(f"Excel combinado: {salida}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel-incidencia", type=Path, required=True)
    parser.add_argument("--datos-inhumacion", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    combinar(args.excel_incidencia, args.datos_inhumacion, args.salida)


if __name__ == "__main__":
    main()

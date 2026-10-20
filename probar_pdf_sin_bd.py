r"""Prueba el PDF de septiembre de 2026 sin modificar PostgreSQL ni el sitio público.

Ejecutar desde ETL-SIEEJ con .venv\Scripts\python.exe
..\reporte_nuevo_para_enviar\probar_pdf_sin_bd.py
"""

from datetime import date, datetime
from pathlib import Path
import sys

import pandas as pd

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
sys.path.insert(0, str(RAIZ / "ETL-SIEEJ"))

from core.pipelines.fosas_clandestinas.stages.transform import FosasClandestinasTransform
from generar_tabla_desde_bd import generar_html


def main() -> None:
    pdf = RAIZ / "tmp" / "pdfs" / "tabla_publica_septiembre_2026.pdf"
    if not pdf.is_file():
        raise SystemExit(f"Falta el PDF: {pdf}")

    corte = date(2026, 9, 1)
    publicacion = pd.DataFrame([{
        "fecha_corte": corte,
        "archivo": pdf.name,
        "url": "https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/wp-content/uploads/2026/10/03-TABLA-PUBLICA-SEPTIEMBRE-2026.pdf",
        "modificado": datetime.fromtimestamp(pdf.stat().st_mtime),
        "ruta": str(pdf),
    }])
    datos = FosasClandestinasTransform().action(publicacion)["stg"]
    if datos.empty or datos["fecha_inicio"].isna().any():
        raise SystemExit("La extracción no devolvió fechas válidas para todos los renglones.")

    # El periodo de oct-18 carece de cifra. No quitar las filas del mismo sitio
    # de diciembre de 2018 y enero de 2019, que sí suman ocho víctimas.
    excluir = (
        datos["consecutivo"].eq(0)
        & datos["fecha_inicio"].eq(date(2018, 10, 1))
        & datos["pre_victimas_loc"].isna()
    )
    if int(excluir.sum()) != 1:
        raise SystemExit("No se encontró exactamente un periodo oct-18 sin cifra.")
    datos_tabla = datos.loc[~excluir]

    agrupados = datos_tabla.groupby("fecha_inicio", sort=True).agg(
        sitios=("consecutivo", "size"),
        victimas=("pre_victimas_loc", "sum"),
    )
    filas = [
        (mes, int(fila.sitios), int(fila.victimas))
        for mes, fila in agrupados.sort_index(ascending=False).iterrows()
    ]
    if sum(f[1] for f in filas) != len(datos_tabla):
        raise SystemExit("La suma mensual de renglones no coincide con el PDF extraído.")

    plantilla = (CARPETA / "reporte_mensual_con_tabla.html").read_text(encoding="utf-8")
    resultado = CARPETA / "vista_previa_sin_bd_2026_09_sin_oct18.html"
    if resultado.exists():
        raise SystemExit(f"Ya existe la vista previa: {resultado}")
    resultado.write_text(generar_html(plantilla, corte, filas), encoding="utf-8")

    septiembre = agrupados.loc[date(2026, 9, 1)]
    print(f"PDF: {pdf.name}")
    print(f"Renglones extraídos: {len(datos)}; incluidos en tabla: {len(datos_tabla)}")
    print(f"Septiembre: {int(septiembre.sitios)} renglones, {int(septiembre.victimas)} víctimas")
    print(f"Meses: {len(filas)}")
    print(f"Vista previa: {resultado}")
    print("No se modificó PostgreSQL ni se publicó el sitio.")


if __name__ == "__main__":
    main()

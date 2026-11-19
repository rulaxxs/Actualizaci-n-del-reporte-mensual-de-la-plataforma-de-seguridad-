r"""Genera juntos el HTML mensual y su descarga Excel desde la base de pruebas.

Se debe indicar el Excel de incidencia del mes. No publica el sitio ni modifica
los archivos de entrada. Requiere openpyxl en el entorno Python del ETL.
"""

import argparse
import calendar
import csv
import json
import os
from datetime import date
from getpass import getpass
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree

from generar_tabla_desde_bd import CARPETA, PLANTILLA, SALIDAS, generar_html, leer_datos


ENLACE_REPORTES = 'href="https://iieg.jalisco.gob.mx/reportes"'
ENLACE_DATOS = (
    'href="https://iieg.jalisco.gob.mx/datos-abiertos/es/dataset/'
    'repositorio-de-datos-de-la-plataforma-de-seguridad-2026"'
)
MESES_CORTOS = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')


def validar_enlaces(html: str) -> None:
    """Confirma que la plantilla conserva los dos enlaces oficiales."""
    if html.count(ENLACE_REPORTES) != 1 or html.count(ENLACE_DATOS) != 1:
        raise ValueError('La plantilla debe tener los enlaces de Reportes y Datos abiertos.')


def etiqueta_mes(mes: date) -> str:
    return f'{MESES_CORTOS[mes.month - 1]}-{mes.year % 100:02d}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--excel-incidencia', type=Path, required=True,
                        help='Excel oficial de incidencia del mes que se conservará como base')
    parser.add_argument('--plantilla', type=Path, default=PLANTILLA,
                        help='HTML base con gráficas del mes; por defecto, reporte_mensual_con_tabla.html')
    parser.add_argument('--salida-dir', type=Path, default=SALIDAS,
                        help='Carpeta principal donde se guardan los paquetes mensuales')
    parser.add_argument('--reemplazar', action='store_true',
                        help='Permite reemplazar un paquete local generado antes')
    parser.add_argument('--usar-rmd', action='store_true',
                        help='Genera el HTML con reporte_mensual_integrado.Rmd y Rscript')
    parser.add_argument('--rscript', default='Rscript',
                        help='Ruta de Rscript si no está en PATH')
    args = parser.parse_args()
    if not args.excel_incidencia.is_file() or args.excel_incidencia.suffix.lower() != '.xlsx':
        parser.error('El Excel de incidencia no existe o no es .xlsx.')
    if not args.plantilla.is_file():
        parser.error(f'No existe la plantilla: {args.plantilla}')
    if args.usar_rmd and not shutil.which(args.rscript):
        parser.error('No se encontró Rscript. Instala R o indica su ruta con --rscript.')
    clave = os.getenv('DB_PASSWORD') or getpass('Contraseña de PostgreSQL (no se mostrará): ')
    if not clave:
        parser.error('No se proporcionó contraseña.')
    corte, filas = leer_datos(clave)
    carpeta = args.salida_dir.resolve() / f'{corte:%Y_%m}'
    ultimo_dia = calendar.monthrange(corte.year, corte.month)[1]
    nombre = f'plataforma_seguridad_al_{ultimo_dia:02d}_{corte.month:02d}_{corte.year}.xlsx'
    excel = carpeta / nombre
    html = carpeta / f'reporte_mensual_{corte:%Y_%m}.html'
    if not args.reemplazar and (excel.exists() or html.exists()):
        raise SystemExit(f'Ya existe el paquete {carpeta}. Usa --reemplazar solo tras revisarlo.')
    carpeta.mkdir(parents=True, exist_ok=True)
    plantilla = args.plantilla.read_text(encoding='utf-8')
    contenido = None if args.usar_rmd else generar_html(plantilla, corte, filas)
    if contenido is not None:
        validar_enlaces(contenido)
    datos = {
        'corte': corte.isoformat(),
        'mensual': [[etiqueta_mes(mes), sitios, victimas] for mes, sitios, victimas in filas],
    }
    with TemporaryDirectory(prefix='reporte_inhumacion_') as temporal:
        json_path = Path(temporal) / 'datos.json'
        excel_temporal = Path(temporal) / nombre
        json_path.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        subprocess.run([
            sys.executable, str(CARPETA / 'combinar_excel_reporte.py'),
            '--excel-incidencia', str(args.excel_incidencia.resolve()),
            '--datos-inhumacion', str(json_path), '--salida', str(excel_temporal),
        ], check=True)
        if not excel_temporal.is_file():
            raise RuntimeError('El generador no creó el Excel.')
        with ZipFile(excel_temporal) as libro:
            if libro.testzip() is not None or 'xl/workbook.xml' not in libro.namelist():
                raise RuntimeError('El Excel generado no pasó la comprobación de integridad.')
            raiz = ElementTree.fromstring(libro.read('xl/workbook.xml'))
            espacio = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
            hojas = [item.attrib['name'] for item in raiz.findall(f'.//{espacio}sheet')]
            if hojas[-1:] != ['Sitios de inhumación'] or 'Inhumación detalle' in hojas:
                raise RuntimeError('El Excel no contiene la hoja de inhumación esperada.')
        if args.usar_rmd:
            csv_temporal = Path(temporal) / 'tabla_inhumacion.csv'
            with csv_temporal.open('w', encoding='utf-8', newline='') as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(('Mes de inicio de procesamiento',
                                   'Número de sitios registrados',
                                   'Total preliminar de víctimas localizadas'))
                escritor.writerows(datos['mensual'])
            ultimo_dia = calendar.monthrange(corte.year, corte.month)[1]
            fecha_titulo = corte.replace(day=ultimo_dia)
            html_generado = Path(temporal) / html.name
            subprocess.run([
                args.rscript, str(CARPETA / 'renderizar_reporte_integrado.R'),
                str(CARPETA / 'reporte_mensual_integrado.Rmd'), str(csv_temporal),
                fecha_titulo.isoformat(), str(html_generado),
            ], check=True)
            if not html_generado.is_file():
                raise RuntimeError('R Markdown no creó el HTML esperado.')
            html_generado.replace(html)
            csv_temporal.replace(carpeta / 'tabla_inhumacion.csv')
        else:
            html_temporal = carpeta / (html.name + '.tmp')
            html_temporal.write_text(contenido, encoding='utf-8')
            html_temporal.replace(html)
        excel_temporal.replace(excel)
    print(f'HTML: {html}')
    print(f'Excel: {excel}')
    print(f'Corte: {corte:%Y-%m}; meses: {len(filas)}')
    print('Paquete local para revisión; no se modificó el sitio público.')


if __name__ == '__main__':
    main()

r"""Genera juntos el HTML mensual y su descarga Excel desde la base de pruebas.

Se debe indicar el Excel de incidencia del mes. No publica el sitio ni modifica
los archivos de entrada. Requiere el mismo entorno Python que el ETL y Node.js
con @oai/artifact-tool disponible en node_modules.
"""

import argparse
import calendar
import csv
import json
import os
from contextlib import closing
from datetime import date
from getpass import getpass
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree

import psycopg2

from generar_tabla_desde_bd import CARPETA, PLANTILLA, generar_html, leer_datos


DESCARGA_ACTUAL = (
    'href="https://iieg.gob.mx/ns/wp-content/uploads/2026/06/'
    'Incidencia-Delictiva-mensual-Mayo-2025-valores.xlsx"'
)
MESES_CORTOS = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')


def enlazar_descarga(html: str, archivo: str) -> str:
    """Cambia únicamente el enlace del botón existente; no toca otras gráficas."""
    if html.count(DESCARGA_ACTUAL) != 1:
        raise ValueError('La plantilla ya no tiene un único enlace de descarga esperado.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.xlsx', archivo):
        raise ValueError('El nombre del Excel no es seguro para un enlace relativo.')
    return html.replace(DESCARGA_ACTUAL, f'href="{archivo}" download', 1)


def etiqueta_mes(mes: date) -> str:
    return f'{MESES_CORTOS[mes.month - 1]}-{mes.year % 100:02d}'


def fecha_mes(mes: date | None) -> str:
    return f'{mes.month:02d}/{mes.year}' if mes else '-'


def leer_detalle(corte: date, clave: str) -> list[list[str | int]]:
    """Lee los renglones completos del mismo corte que alimenta la tabla HTML."""
    base = os.getenv('DB_NAME', 'fosas_clandestinas_pruebas')
    if base != 'fosas_clandestinas_pruebas':
        raise ValueError('Solo se admite la base local fosas_clandestinas_pruebas.')
    with closing(psycopg2.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '5432')),
        dbname=base,
        user=os.getenv('DB_USER', 'postgres'),
        password=clave,
    )) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute('SELECT id, fecha_corte FROM cat_publicaciones ORDER BY fecha_corte DESC LIMIT 1')
            publicacion = cursor.fetchone()
            if publicacion is None or publicacion[1] != corte:
                raise ValueError('El corte más reciente cambió durante la generación. Repite el proceso.')
            cursor.execute(
                'SELECT s.consecutivo, s.periodo, s.denominacion, m.nomgeo, '
                's.fecha_inicio, s.fecha_fin, s.en_proceso, '
                's.pre_victimas_loc, s.pre_victimas_ide, s.pre_hom_ide, '
                's.pre_muj_ide, s.estatus_loc '
                'FROM stg_fosas_clandestinas AS s '
                'LEFT JOIN cvegeo_municipalities AS m '
                'ON m.cve_ent = s.cve_ent AND m.cve_mun = s.cve_mun '
                'WHERE s.publicacion_id = %s ORDER BY s.consecutivo, s.periodo',
                (publicacion[0],),
            )
            registros = cursor.fetchall()
            cursor.execute(
                'SELECT COUNT(*) FROM stg_fosas_clandestinas WHERE publicacion_id = %s',
                (publicacion[0],),
            )
            esperado = cursor.fetchone()[0]
    if not registros or len(registros) != esperado:
        raise ValueError('La tabla detallada está vacía o el cruce municipal duplicó registros.')

    detalle = []
    for (registro, _periodo, nombre, municipio, inicio, fin, en_proceso,
         localizadas, identificadas, hombres, mujeres, estatus) in registros:
        if inicio and inicio > corte:
            raise ValueError('Hay una fecha de procesamiento posterior al corte.')
        detalle.append([
            'oct-18' if registro == 0 else registro,
            nombre or '-', municipio or '-', fecha_mes(inicio),
            'EN PROCESO' if en_proceso else fecha_mes(fin),
            localizadas if localizadas is not None else (estatus or '-'),
            identificadas if identificadas is not None else '-',
            hombres if hombres is not None else '-',
            mujeres if mujeres is not None else '-',
        ])
    return detalle


def buscar_node() -> str:
    instalado = shutil.which('node')
    if instalado:
        return instalado
    incluido = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    if incluido.is_file():
        return str(incluido)
    raise FileNotFoundError('Falta Node.js para crear el Excel.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--excel-incidencia', type=Path, required=True,
                        help='Excel oficial de incidencia del mes que se conservará como base')
    parser.add_argument('--salida-dir', type=Path, default=CARPETA,
                        help='Carpeta donde se creará el paquete HTML + Excel')
    parser.add_argument('--reemplazar', action='store_true',
                        help='Permite reemplazar un paquete local generado antes')
    parser.add_argument('--usar-rmd', action='store_true',
                        help='Genera el HTML con reporte_mensual_integrado.Rmd y Rscript')
    parser.add_argument('--rscript', default='Rscript',
                        help='Ruta de Rscript si no está en PATH')
    args = parser.parse_args()
    if not args.excel_incidencia.is_file() or args.excel_incidencia.suffix.lower() != '.xlsx':
        parser.error('El Excel de incidencia no existe o no es .xlsx.')
    if args.usar_rmd and not shutil.which(args.rscript):
        parser.error('No se encontró Rscript. Instala R o indica su ruta con --rscript.')
    clave = os.getenv('DB_PASSWORD') or getpass('Contraseña de PostgreSQL (no se mostrará): ')
    if not clave:
        parser.error('No se proporcionó contraseña.')
    corte, filas = leer_datos(clave)
    detalle = leer_detalle(corte, clave)
    carpeta = args.salida_dir.resolve() / f'reporte_generado_{corte:%Y_%m}'
    nombre = f'reporte_mensual_{corte:%Y_%m}.xlsx'
    excel = carpeta / nombre
    html = carpeta / f'reporte_mensual_{corte:%Y_%m}.html'
    if not args.reemplazar and (excel.exists() or html.exists()):
        raise SystemExit(f'Ya existe el paquete {carpeta}. Usa --reemplazar solo tras revisarlo.')
    carpeta.mkdir(parents=True, exist_ok=True)
    plantilla = PLANTILLA.read_text(encoding='utf-8')
    contenido = None if args.usar_rmd else enlazar_descarga(generar_html(plantilla, corte, filas), nombre)
    datos = {
        'corte': corte.isoformat(),
        'mensual': [[etiqueta_mes(mes), sitios, victimas] for mes, sitios, victimas in filas],
        'detalle': detalle,
    }
    with TemporaryDirectory(prefix='reporte_inhumacion_') as temporal:
        json_path = Path(temporal) / 'datos.json'
        excel_temporal = Path(temporal) / nombre
        json_path.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        resultado = subprocess.run([
            buscar_node(), str(CARPETA / 'combinar_excel_reporte.mjs'),
            '--excel-incidencia', str(args.excel_incidencia.resolve()),
            '--datos-inhumacion', str(json_path), '--salida', str(excel_temporal),
        ], check=False)
        if not excel_temporal.is_file():
            raise RuntimeError(f'El generador no creó el Excel (código {resultado.returncode}).')
        with ZipFile(excel_temporal) as libro:
            if libro.testzip() is not None or 'xl/workbook.xml' not in libro.namelist():
                raise RuntimeError('El Excel generado no pasó la comprobación de integridad.')
            raiz = ElementTree.fromstring(libro.read('xl/workbook.xml'))
            espacio = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
            hojas = [item.attrib['name'] for item in raiz.findall(f'.//{espacio}sheet')]
            if hojas[-2:] != ['Inhumación mensual', 'Inhumación detalle']:
                raise RuntimeError('El Excel no contiene las dos hojas de inhumación esperadas.')
        # El runtime incluido con Codex puede terminar con un código no cero
        # después de guardar. Solo se continúa si el archivo pasó la prueba ZIP
        # y contiene las dos hojas esperadas; la anomalía se deja visible.
        if resultado.returncode != 0:
            print(f'Advertencia: Node.js terminó con código {resultado.returncode}, '
                  'pero el Excel generado pasó la verificación de integridad.')
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
                fecha_titulo.isoformat(), nombre, str(html_generado),
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
    print(f'Corte: {corte:%Y-%m}; meses: {len(filas)}; detalle: {len(detalle)} renglones')
    print('Paquete local para revisión; no se modificó el sitio público.')


if __name__ == '__main__':
    main()

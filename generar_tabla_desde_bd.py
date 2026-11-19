r"""Genera una copia del reporte con la tabla mensual tomada de PostgreSQL.

Uso local (desde la carpeta ETL-SIEEJ):
    .\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_tabla_desde_bd.py

No modifica el HTML original ni publica el resultado. Solo consulta la base.
"""

import argparse
import calendar
from contextlib import closing
from datetime import date
from getpass import getpass
from html import escape
import os
from pathlib import Path
import re

import psycopg2


CARPETA = Path(__file__).resolve().parent
PLANTILLA = CARPETA / "reporte_mensual_con_tabla.html"
SALIDAS = CARPETA / "reportes_generados"
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
ABREVIATURAS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
TITULO = "Sitios de inhumación clandestina registrados en Jalisco, al corte del "
ENCABEZADOS = (
    "Mes de inicio de procesamiento",
    "Número de sitios registrados",
    "Total preliminar de víctimas localizadas",
)
FILA = re.compile(r"<tr\b[^>]*>.*?</tr>", re.DOTALL)
CELDA = re.compile(r"(<td\b[^>]*>)(.*?)(</td>)", re.DOTALL)
MES_ESPECIAL_SIN_CIFRA = date(2018, 10, 1)


def omitir_registro_oct18_sin_cifra(
    filas: list[tuple[date, int, int]], cantidad: int
) -> list[tuple[date, int, int]]:
    """Resta solo el periodo sin cifra de oct-18; conserva los demás periodos del sitio."""
    if cantidad not in (0, 1):
        raise ValueError("Se encontró más de un registro especial oct-18 sin cifra.")
    if not cantidad:
        return filas
    resultado = []
    encontrado = False
    for mes, sitios, victimas in filas:
        if mes == MES_ESPECIAL_SIN_CIFRA:
            if sitios < 1:
                raise ValueError("El registro oct-18 no figura en la vista mensual.")
            encontrado = True
            if sitios > 1:
                resultado.append((mes, sitios - 1, victimas))
        else:
            resultado.append((mes, sitios, victimas))
    if not encontrado:
        raise ValueError("El registro oct-18 no figura en la vista mensual.")
    return resultado


def leer_datos(clave: str | None = None) -> tuple[date, list[tuple[date, int, int]]]:
    """Lee la última publicación y verifica que la vista mensual esté actualizada."""
    base = os.getenv("DB_NAME", "fosas_clandestinas_pruebas")
    if base != "fosas_clandestinas_pruebas":
        raise ValueError("Esta primera prueba solo admite fosas_clandestinas_pruebas.")
    clave = clave or os.getenv("DB_PASSWORD") or getpass("Contraseña de PostgreSQL (no se mostrará): ")
    if not clave:
        raise ValueError("No se proporcionó contraseña.")

    with closing(
        psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=base,
            user=os.getenv("DB_USER", "postgres"),
            password=clave,
        )
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != base:
                raise ValueError("La conexión llegó a una base inesperada.")

            cursor.execute("SELECT id, fecha_corte FROM cat_publicaciones ORDER BY fecha_corte DESC LIMIT 1")
            publicacion = cursor.fetchone()
            if publicacion is None:
                raise ValueError("No hay publicaciones cargadas en la base de pruebas.")
            publicacion_id, corte = publicacion

            cursor.execute(
                "SELECT ispopulated FROM pg_matviews "
                "WHERE schemaname = 'public' AND matviewname = 'vwm_fosas_clandestinas_mensual'"
            )
            estado = cursor.fetchone()
            if estado is None or not estado[0]:
                raise ValueError("La vista mensual aún no contiene datos.")

            cursor.execute(
                "SELECT fecha_periodo_seleccion, sitios_inhumacion_clandestina, "
                "total_preliminar_victimas_localizadas "
                "FROM vwm_fosas_clandestinas_mensual ORDER BY fecha_periodo_seleccion DESC"
            )
            filas = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(pre_victimas_loc), 0) "
                "FROM stg_fosas_clandestinas "
                "WHERE publicacion_id = %s AND fecha_inicio IS NOT NULL",
                (publicacion_id,),
            )
            conteo_origen, victimas_origen = cursor.fetchone()
            cursor.execute(
                "SELECT COUNT(*) FROM stg_fosas_clandestinas "
                "WHERE publicacion_id = %s AND consecutivo = 0 "
                "AND fecha_inicio = %s AND pre_victimas_loc IS NULL",
                (publicacion_id, MES_ESPECIAL_SIN_CIFRA),
            )
            exclusiones_oct18 = cursor.fetchone()[0]

    if not filas:
        raise ValueError("La vista mensual no devolvió meses.")
    if sum(f[1] for f in filas) != conteo_origen or sum(f[2] for f in filas) != victimas_origen:
        raise ValueError("La vista mensual no coincide con la última publicación. No se generó el reporte.")
    if len({f[0] for f in filas}) != len(filas):
        raise ValueError("Hay meses duplicados en la vista mensual.")
    if any(f[0].day != 1 or f[0] > corte or f[1] < 0 or f[2] < 0 for f in filas):
        raise ValueError("La vista mensual contiene fechas o cifras inesperadas.")
    return corte, omitir_registro_oct18_sin_cifra(filas, exclusiones_oct18)


def sustituir_celdas(plantilla_fila: str, valores: tuple[str, int, int]) -> str:
    datos = iter(valores)

    def reemplazar(coincidencia: re.Match[str]) -> str:
        return coincidencia.group(1) + escape(str(next(datos))) + coincidencia.group(3)

    nueva, cantidad = CELDA.subn(reemplazar, plantilla_fila)
    if cantidad != 3:
        raise ValueError("Una fila de la tabla no tiene exactamente tres celdas.")
    return nueva


def generar_html(html_original: str, corte: date, filas: list[tuple[date, int, int]]) -> str:
    """Cambia únicamente el título y las filas de la tabla de inhumación."""
    if html_original.count(TITULO) != 1:
        raise ValueError("No se encontró un título único para la tabla.")
    inicio_titulo = html_original.index(TITULO)
    fin_titulo = html_original.index("</p>", inicio_titulo)
    ultimo_dia = calendar.monthrange(corte.year, corte.month)[1]
    titulo_nuevo = f"{TITULO}{ultimo_dia} de {MESES[corte.month - 1]} de {corte.year}"
    html = html_original[:inicio_titulo] + titulo_nuevo + html_original[fin_titulo:]

    inicio_tabla = html.index("<table", inicio_titulo)
    fin_tabla = html.index("</table>", inicio_tabla)
    tabla = html[inicio_tabla:fin_tabla]
    if any(encabezado not in tabla for encabezado in ENCABEZADOS):
        raise ValueError("Los encabezados de la tabla no son los esperados.")
    inicio_tbody = html.index("<tbody>", inicio_tabla) + len("<tbody>")
    fin_tbody = html.index("</tbody>", inicio_tbody)
    if fin_tbody > fin_tabla:
        raise ValueError("No se encontró el cuerpo de la tabla esperada.")
    plantillas = FILA.findall(html[inicio_tbody:fin_tbody])
    if len(plantillas) < 2:
        raise ValueError("Faltan las dos filas de estilo de la tabla original.")

    filas_html = []
    for indice, (mes, sitios, victimas) in enumerate(filas):
        etiqueta = f"{ABREVIATURAS[mes.month - 1]}-{mes.year % 100:02d}"
        filas_html.append(sustituir_celdas(plantillas[indice % 2], (etiqueta, sitios, victimas)))
    return html[:inicio_tbody] + "\n" + "\n".join(filas_html) + "\n" + html[fin_tbody:]


def main() -> None:
    opciones = argparse.ArgumentParser(description=__doc__)
    opciones.add_argument("--reemplazar", action="store_true", help="Permitir sustituir un archivo ya generado")
    opciones.add_argument("--plantilla", type=Path, default=PLANTILLA,
                          help="HTML base del reporte; por defecto, reporte_mensual_con_tabla.html")
    opciones.add_argument("--salida-dir", type=Path, default=SALIDAS,
                          help="Carpeta principal para reportes generados")
    argumentos = opciones.parse_args()
    if not argumentos.plantilla.is_file():
        opciones.error(f"No existe la plantilla: {argumentos.plantilla}")

    corte, filas = leer_datos()
    salida = argumentos.salida_dir.resolve() / f"{corte:%Y_%m}" / f"reporte_mensual_generado_{corte:%Y_%m}.html"
    if salida.exists() and not argumentos.reemplazar:
        raise SystemExit(f"Ya existe {salida}. Usa --reemplazar solo si deseas sobrescribirlo.")
    original = argumentos.plantilla.read_text(encoding="utf-8")
    generado = generar_html(original, corte, filas)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(generado, encoding="utf-8")
    print(f"Generado: {salida}")
    print(f"Corte: {corte:%Y-%m}; meses: {len(filas)}; sitios/periodos: {sum(f[1] for f in filas)}")
    print("Solo se actualizó la tabla de inhumación y su título; el sitio público no cambió.")


if __name__ == "__main__":
    main()

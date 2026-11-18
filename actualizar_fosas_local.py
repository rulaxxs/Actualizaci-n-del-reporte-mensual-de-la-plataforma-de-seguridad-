r"""Valida un PDF nuevo de Fiscalía y, con --cargar, lo agrega a PostgreSQL local.

Ejecutar desde ETL-SIEEJ con su entorno virtual:
    .\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_local.py --pdf "C:\ruta\tabla.pdf" --corte AAAA-MM --url "https://..."

Sin --cargar no modifica la base. El comando solo admite la base local de pruebas.
"""

import argparse
from datetime import date, datetime
from getpass import getpass
import os
from pathlib import Path
import sys
from urllib.parse import quote, unquote, urlparse

import pandas as pd
import psycopg2


CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent / "ETL-SIEEJ"))
BASE_ESPERADA = "fosas_clandestinas_pruebas"
HOSTS_LOCALES = {"127.0.0.1", "localhost"}
HOST_FUENTE = "fiscaliaenpersonasdesaparecidas.jalisco.gob.mx"


def interpretar_corte(valor: str) -> date:
    try:
        return date.fromisoformat(f"{valor}-01")
    except ValueError as error:
        raise argparse.ArgumentTypeError("Usa --corte AAAA-MM, por ejemplo 2026-10.") from error


def verificar_nombre_corte(nombre: str, corte: date) -> None:
    from core.pipelines.fosas_clandestinas.constants import CUTOFF_RE, MONTHS

    encontrado = CUTOFF_RE.search(nombre.upper())
    if encontrado:
        detectado = date(int(encontrado.group(2)), MONTHS[encontrado.group(1)], 1)
        if detectado != corte:
            raise ValueError(
                f"El archivo {nombre!r} indica {detectado:%Y-%m}, distinto de --corte {corte:%Y-%m}."
            )
    else:
        print(f"Aviso: no pude leer el corte del nombre {nombre!r}; confírmalo en el PDF.")


def preparar_publicacion(pdf: Path, corte: date, url: str | None) -> pd.DataFrame:
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise ValueError(f"No existe el PDF indicado: {pdf}")
    with pdf.open("rb") as archivo:
        if archivo.read(5) != b"%PDF-":
            raise ValueError("El archivo indicado no tiene encabezado PDF.")
    verificar_nombre_corte(pdf.name, corte)

    if url:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != HOST_FUENTE:
            raise ValueError(f"--url debe ser un enlace HTTPS del dominio {HOST_FUENTE}.")
        verificar_nombre_corte(unquote(Path(parsed.path).name), corte)

    return pd.DataFrame([{
        "fecha_corte": corte,
        "archivo": pdf.name,
        "url": url or "",
        # El PDF descargado no contiene el Last-Modified del servidor.
        # Esta fecha local es solo metadato de la prueba, no fecha oficial.
        "modificado": datetime.fromtimestamp(pdf.stat().st_mtime),
        "ruta": str(pdf),
    }])


def validar_base(settings, clave: str, corte: date) -> date | None:
    if (
        settings.DB_NAME != BASE_ESPERADA
        or settings.DB_HOST not in HOSTS_LOCALES
        or str(settings.DB_PORT) != "5432"
    ):
        raise ValueError(
            "La configuración no apunta a la base local de pruebas "
            f"(host={settings.DB_HOST}, puerto={settings.DB_PORT}, base={settings.DB_NAME})."
        )

    conexion = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=clave,
        connect_timeout=5,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != BASE_ESPERADA:
                raise ValueError("La conexión llegó a otra base; no se cargó nada.")
            cursor.execute("SELECT MAX(fecha_corte) FROM cat_publicaciones")
            anterior = cursor.fetchone()[0]
            if anterior is not None and corte <= anterior:
                raise ValueError(
                    f"El corte {corte:%Y-%m} no es posterior al último cargado "
                    f"({anterior:%Y-%m}); no se reemplazará ningún corte."
                )
            cursor.execute("SELECT COUNT(*) FROM cvegeo_municipalities")
            if cursor.fetchone()[0] == 0:
                raise ValueError("El catálogo de municipios está vacío; no se cargó nada.")
            return anterior
    finally:
        conexion.close()


def preparar_clave_para_cargador(settings, clave: str) -> None:
    """Codifica la clave para la URL que construye BaseConfig.database_url."""
    settings.DB_PASSWORD = quote(clave, safe="")


def verificar_carga(settings, clave: str, corte: date, filas_esperadas: int) -> int:
    conexion = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=clave,
        connect_timeout=5,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT MAX(fecha_corte) FROM cat_publicaciones")
            ultimo = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM stg_fosas_clandestinas AS s "
                "JOIN cat_publicaciones AS p ON p.id = s.publicacion_id "
                "WHERE p.fecha_corte = %s",
                (corte,),
            )
            filas = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vwm_fosas_clandestinas_mensual")
            meses = cursor.fetchone()[0]
    finally:
        conexion.close()
    if ultimo != corte or filas != filas_esperadas or meses == 0:
        raise RuntimeError(
            f"La verificación posterior no coincide: corte={ultimo}, filas={filas}, meses={meses}. "
            "No generes el HTML hasta revisar la base."
        )
    return meses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True, help="PDF oficial descargado")
    parser.add_argument("--corte", type=interpretar_corte, required=True, help="Mes de corte AAAA-MM")
    parser.add_argument("--url", help="URL oficial HTTPS del mismo PDF (obligatoria con --cargar)")
    parser.add_argument("--cargar", action="store_true", help="Después de validar, cargar en PostgreSQL local")
    args = parser.parse_args()
    if args.cargar and not args.url:
        parser.error("--cargar requiere --url para registrar la fuente oficial.")

    pdf = args.pdf.resolve()
    publicacion = preparar_publicacion(pdf, args.corte, args.url)
    from core.pipelines.fosas_clandestinas.stages.transform import FosasClandestinasTransform

    transformados = FosasClandestinasTransform().action(publicacion)
    filas = transformados["stg"]
    if filas.empty or filas["fecha_inicio"].isna().any():
        raise ValueError("El ETL no pudo extraer filas válidas con fecha de inicio; no se cargó nada.")
    if filas["fecha_inicio"].gt(args.corte).any():
        raise ValueError("Hay fechas de inicio posteriores al corte; no se cargó nada.")
    print(
        f"Validación: corte {args.corte:%Y-%m}; {len(filas)} renglones; "
        f"{filas['consecutivo'].nunique()} sitios registrados en el PDF."
    )
    print("Compara estas cifras con el PDF antes de cargar.")
    if not args.cargar:
        print("Solo validación: PostgreSQL no se modificó. Usa --cargar después de revisar.")
        return

    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", BASE_ESPERADA)
    clave = os.getenv("DB_PASSWORD") or getpass("Contraseña de PostgreSQL (no se mostrará): ")
    if not clave:
        raise ValueError("No se proporcionó contraseña; no se cargó nada.")
    os.environ["DB_PASSWORD"] = clave
    from core.pipelines.fosas_clandestinas.config import settings
    from core.pipelines.fosas_clandestinas.stages.load import FosasClandestinasLoad

    anterior = validar_base(settings, clave, args.corte)
    print(f"Base verificada: {settings.DB_NAME}; último corte: {anterior or 'ninguno'}.")
    preparar_clave_para_cargador(settings, clave)
    carga = FosasClandestinasLoad(mode="update")
    try:
        cargadas = carga.action(transformados)
    finally:
        carga.db.disconnect()
    if cargadas != len(filas):
        raise RuntimeError("El ETL reportó un número distinto de renglones cargados.")
    meses = verificar_carga(settings, clave, args.corte, len(filas))
    print(f"Carga terminada: {cargadas} renglones; {meses} meses en la vista.")
    print("El sitio público no se modificó. Ahora puedes generar el HTML desde PostgreSQL.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, psycopg2.Error) as error:
        raise SystemExit(f"Error: {error}") from None

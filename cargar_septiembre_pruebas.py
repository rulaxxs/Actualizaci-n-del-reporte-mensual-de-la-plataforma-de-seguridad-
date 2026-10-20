r"""Carga el PDF oficial de septiembre de 2026 solo en la base local de pruebas.

Ejecutar desde ETL-SIEEJ:
    .\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\cargar_septiembre_pruebas.py
"""

from datetime import date, datetime
from getpass import getpass
import os
from pathlib import Path
import sys

import pandas as pd
import psycopg2


CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
sys.path.insert(0, str(RAIZ / "ETL-SIEEJ"))

BASE_ESPERADA = "fosas_clandestinas_pruebas"
CORTE = date(2026, 9, 1)
PDF = RAIZ / "tmp" / "pdfs" / "tabla_publica_septiembre_2026.pdf"
URL = (
    "https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/"
    "wp-content/uploads/2026/10/03-TABLA-PUBLICA-SEPTIEMBRE-2026.pdf"
)


def main() -> None:
    if not PDF.is_file():
        raise SystemExit(f"Falta el PDF oficial descargado: {PDF}")
    # El ETL usa por defecto localhost/sieej. Para esta prueba aislada,
    # proporcionar los valores seguros solo cuando no fueron definidos.
    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", BASE_ESPERADA)
    if not os.environ.get("DB_PASSWORD"):
        os.environ["DB_PASSWORD"] = getpass("Contraseña de PostgreSQL (no se mostrará): ")
    if not os.environ["DB_PASSWORD"]:
        raise SystemExit("No se proporcionó contraseña; no se cargó nada.")

    # Importar la configuración después de establecer DB_PASSWORD.
    from core.pipelines.fosas_clandestinas.config import settings
    from core.pipelines.fosas_clandestinas.stages.load import FosasClandestinasLoad
    from core.pipelines.fosas_clandestinas.stages.transform import FosasClandestinasTransform

    if (
        settings.DB_NAME != BASE_ESPERADA
        or settings.DB_HOST != "127.0.0.1"
        or str(settings.DB_PORT) != "5432"
    ):
        raise SystemExit(
            "La configuración no apunta a la base local de pruebas "
            f"(host={settings.DB_HOST}, puerto={settings.DB_PORT}, base={settings.DB_NAME}); "
            "no se cargó nada."
        )

    conexion = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != BASE_ESPERADA:
                raise SystemExit("La conexión llegó a otra base; no se cargó nada.")
            cursor.execute("SELECT COUNT(*) FROM cat_publicaciones WHERE fecha_corte = %s", (CORTE,))
            if cursor.fetchone()[0]:
                raise SystemExit("Septiembre ya está cargado. No se reemplazará sin revisarlo.")
            cursor.execute("SELECT COUNT(*) FROM cat_publicaciones WHERE fecha_corte = %s", (date(2026, 8, 1),))
            if cursor.fetchone()[0] != 1:
                raise SystemExit("No se encontró la carga previa de agosto; no se cargó nada.")
    finally:
        conexion.close()

    publicacion = pd.DataFrame([{
        "fecha_corte": CORTE,
        "archivo": PDF.name,
        "url": URL,
        # Valor local de prueba; no representa la fecha oficial de modificación.
        "modificado": datetime.fromtimestamp(PDF.stat().st_mtime),
        "ruta": str(PDF),
    }])
    transformados = FosasClandestinasTransform().action(publicacion)
    filas = transformados["stg"]
    if (
        len(filas) != 265
        or filas["consecutivo"].nunique() != 261
        or len(filas.loc[filas["fecha_inicio"].eq(CORTE)]) != 2
    ):
        raise SystemExit("La extracción no coincide con la prueba previa; no se cargó nada.")

    carga = FosasClandestinasLoad(mode="update")
    try:
        cargadas = carga.action(transformados)
    finally:
        carga.db.disconnect()

    conexion = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT fecha_corte FROM cat_publicaciones ORDER BY fecha_corte DESC LIMIT 1")
            ultimo_corte = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM stg_fosas_clandestinas f "
                "JOIN cat_publicaciones p ON p.id = f.publicacion_id "
                "WHERE p.fecha_corte = %s",
                (CORTE,),
            )
            filas_db = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vwm_fosas_clandestinas_mensual")
            meses_vista = cursor.fetchone()[0]
    finally:
        conexion.close()

    if ultimo_corte != CORTE or filas_db != 265:
        raise SystemExit("La carga terminó, pero la verificación posterior no coincide. No generes el HTML todavía.")
    print(f"Carga de prueba terminada: {cargadas} renglones; corte {ultimo_corte}; {meses_vista} meses en la vista.")
    print("Agosto se conservó. No se modificó el sitio público.")


if __name__ == "__main__":
    main()

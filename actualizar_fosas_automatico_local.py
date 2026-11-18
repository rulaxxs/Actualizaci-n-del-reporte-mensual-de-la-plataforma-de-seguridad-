r"""Descubre el PDF oficial nuevo y usa las etapas del ETL sin Airflow.

Desde ETL-SIEEJ:
    .\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10
    .\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10 --cargar

Sin --cargar solo descubre, descarga, transforma y valida; no escribe en PostgreSQL.
"""

import argparse
from getpass import getpass
import os
from pathlib import Path
import sys

import psycopg2


CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent / "ETL-SIEEJ"))

from actualizar_fosas_local import (  # noqa: E402
    BASE_ESPERADA,
    interpretar_corte,
    preparar_clave_para_cargador,
    validar_base,
    verificar_carga,
    verificar_nombre_corte,
)
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corte", type=interpretar_corte, required=True, help="Corte esperado AAAA-MM")
    parser.add_argument("--cargar", action="store_true", help="Cargar el corte validado en la base local de pruebas")
    args = parser.parse_args()

    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", BASE_ESPERADA)
    from core.pipelines.fosas_clandestinas.stages.extract import FosasClandestinasExtract
    from core.pipelines.fosas_clandestinas.stages.transform import FosasClandestinasTransform

    clave = None
    if args.cargar:
        clave = os.getenv("DB_PASSWORD") or getpass("Contraseña de PostgreSQL (no se mostrará): ")
        if not clave:
            raise ValueError("No se proporcionó contraseña; no se cargó nada.")
        os.environ["DB_PASSWORD"] = clave
        from core.pipelines.fosas_clandestinas.config import settings

        anterior = validar_base(settings, clave, args.corte)
        print(f"Base verificada: {settings.DB_NAME}; último corte: {anterior or 'ninguno'}.")

    # source() descubre el registro en el servidor; action() descarga el PDF.
    extractor = FosasClandestinasExtract()
    publicaciones = [p for p in extractor.source() if p["fecha_corte"] == args.corte]
    if len(publicaciones) != 1:
        raise ValueError(
            f"Se esperaban una publicación para {args.corte:%Y-%m}; se encontraron {len(publicaciones)}. "
            "No se cargó nada. Revisa la página oficial y el listado del servidor."
        )
    publicacion = publicaciones[0]
    verificar_nombre_corte(publicacion["archivo"], args.corte)
    print(f"Fuente: {publicacion['url']}")
    descargadas = extractor.action(publicaciones)

    import pandas as pd

    transformados = FosasClandestinasTransform().action(pd.DataFrame(descargadas))
    filas = transformados["stg"]
    if filas.empty or filas["fecha_inicio"].isna().any():
        raise ValueError("El ETL no pudo extraer filas válidas con fecha de inicio; no se cargó nada.")
    if filas["fecha_inicio"].gt(args.corte).any():
        raise ValueError("Hay fechas de inicio posteriores al corte; no se cargó nada.")
    numerados = filas.loc[filas["consecutivo"] > 0, "consecutivo"].nunique()
    especial = filas["consecutivo"].eq(0).any()
    print(
        f"Validación: corte {args.corte:%Y-%m}; {len(filas)} renglones; "
        f"{numerados} sitios numerados"
        + (" y un registro especial sin número (oct-18)." if especial else ".")
    )
    print("Compara estas cifras con el PDF oficial antes de cargar.")
    if not args.cargar:
        print("Solo validación: PostgreSQL no se modificó. Repite con --cargar después de revisar.")
        return

    from core.pipelines.fosas_clandestinas.stages.load import FosasClandestinasLoad

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
    print("La base local está actualizada. El HTML y el sitio público no se modificaron.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, psycopg2.Error) as error:
        raise SystemExit(f"Error: {error}") from None

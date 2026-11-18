# Cómo se actualiza la tabla de inhumación

Esta guía distingue el ETL de la generación del reporte mensual. El PDF de Fiscalía es la fuente; el HTML es un resultado para revisión y publicación. La base local `fosas_clandestinas_pruebas` no alimenta directamente al sitio publicado.

## Flujo previsto

```text
Página de Fiscalía / directorio de publicaciones
          ↓
ETL-SIEEJ: extract → transform → load
          ↓
PostgreSQL: publicaciones, registros y vista mensual
          ↓
Generador de este repositorio
          ↓
HTML (y, cuando se solicita, Excel) → revisión → publicación
```

1. **Extract:** `ETL-SIEEJ/core/pipelines/fosas_clandestinas/stages/extract.py` recorre el índice de archivos del servidor de Fiscalía por año y mes. Reconoce los PDF del registro, obtiene el mes de corte del nombre, selecciona una publicación por corte y, en modo actualización, descarga solo cortes posteriores al último cargado. Guarda el PDF en `data/extract/fosas_clandestinas/`. Esta etapa depende del formato del listado del directorio web; si Fiscalía lo cambia, habrá que adaptar el extractor.
2. **Transform:** `stages/transform.py` lee las tablas con `pdfplumber`, normaliza fechas, sitios, municipios y cifras, y prepara un registro completo de la publicación.
3. **Load:** `stages/load.py` guarda la publicación y sus renglones en PostgreSQL, resuelve las claves municipales y refresca `vwm_fosas_clandestinas_mensual`. El modo `update` conserva los cortes anteriores; `bootstrap` reinicia las tablas y se reserva para la carga inicial.
4. **Reporte:** `generar_tabla_desde_bd.py` consulta la última publicación en PostgreSQL y escribe una copia del HTML con la tabla actualizada. `generar_reporte_con_excel.py` también prepara el Excel del reporte cuando recibe el Excel de incidencia. Los demás gráficos provienen del HTML o del R Markdown, no de este ETL.

Cada PDF contiene el registro completo desde 2018. La vista mensual toma la publicación más reciente para evitar sumar varios cortes. El mes de una fila corresponde al inicio de procesamiento, no al mes de descarga. Por ejemplo, `03-TABLA-PUBLICA-OCTUBRE-2026.pdf` está en una carpeta de noviembre y corresponde al corte de octubre de 2026.

## Cómo se ejecuta hoy

- **Con Airflow:** `ETL-SIEEJ/dags/etl_fosas_clandestinas.py` define `etl_fosas_clandestinas_update` con las tareas `extract → transform → load`. Este flujo descubre y descarga los PDF automáticamente. `etl_fosas_clandestinas_bootstrap` es para la carga inicial y no tiene programación mensual.
- **En esta computadora, sin Airflow:** `actualizar_fosas_automatico_local.py` llama al extractor para descubrir y descargar el PDF del corte indicado, lo transforma y opcionalmente lo carga en `fosas_clandestinas_pruebas`. Sin `--cargar` no escribe en PostgreSQL. También existe `actualizar_fosas_local.py` para usar un PDF ya descargado cuando el listado automático no esté disponible. Los comandos están en el [README](README.md#actualizar-desde-la-fuente-oficial-sin-airflow).
- **No usar:** `python -m core.pipelines.fosas_clandestinas update`; esta copia del paquete no contiene `__main__.py`. La instrucción que aparece en el README del ETL no funciona aquí.

## Estado de la prueba local

El comando automático ya está creado. En la computadora del usuario descubrió y descargó el PDF oficial de octubre de 2026, cargó 266 renglones y refrescó la vista mensual con 88 meses. Son 261 sitios numerados y un registro especial sin número (`oct-18`) con tres periodos. La verificación posterior confirmó el corte y las 266 filas en PostgreSQL. Luego se incorporaron las gráficas del HTML mensual recibido y se generó `reporte_mensual_generado_2026_10.html` con 87 meses visibles; el sitio público no se modificó. El comando de PDF manual sigue disponible como alternativa.

## Comprobaciones del corte

Después de cargar, verificar en `cat_publicaciones` el último `fecha_corte`, comparar el número de renglones con el PDF y revisar `vwm_fosas_clandestinas_mensual`. Luego generar el HTML, revisar la tabla y la fecha, y publicar mediante el procedimiento del equipo. Ejecutar el ETL no modifica automáticamente el HTML ni el sitio público.

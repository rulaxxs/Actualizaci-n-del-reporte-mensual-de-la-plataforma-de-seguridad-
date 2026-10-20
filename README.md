# Reporte mensual: tabla y descarga de sitios de inhumación clandestina

Este repositorio local contiene el reporte HTML y un generador para actualizar la tabla mensual de inhumación con datos de PostgreSQL. También puede preparar, en un solo paso, el HTML y el Excel descargable con las dos hojas de inhumación. Todavía no es una publicación automática.

## Estado actual

- Fuente oficial: [Registro Estatal de Fosas Clandestinas de Jalisco](https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/registro-estatal-de-fosas-clandestinas/).
- Cortes probados: agosto y septiembre de 2026. Septiembre se cargó en la base de pruebas y se generó el HTML local; el sitio público no se actualizó con ese corte.
- Base usada: `fosas_clandestinas_pruebas`, en PostgreSQL local.
- Septiembre: 265 renglones extraídos; 264 incluidos en la tabla después de omitir el periodo `oct-18` sin cifra; 86 meses visibles.
- Sitio publicado: [reporte mensual](https://reporte-mensual-inhumacion-jalisco.alive-fawn-1254.chatgpt.site/). Es una copia estática: no se conecta a PostgreSQL cuando alguien la visita.

## Archivos principales

| Archivo | Para qué sirve |
| --- | --- |
| `reporte_mensual_con_tabla.html` | Plantilla del reporte completo. La tabla de inhumación está entre la comparativa de delitos contra la vida y el mapa de tasas delictivas; conserva las demás gráficas y contenido. |
| `generar_tabla_desde_bd.py` | Lee la última publicación de la base de pruebas, verifica los totales y sustituye el título y las filas de la tabla. |
| `generar_reporte_con_excel.py` | Recibe el Excel de incidencia del mes, consulta la última publicación de inhumación y genera juntos el HTML y el Excel combinado. |
| `reporte_mensual_integrado.Rmd` | Copia del R Markdown recibido; reemplaza la tabla antigua de fosas por el CSV mensual preparado por Python y coloca la tabla entre la comparativa de vida y el mapa. |
| `renderizar_reporte_integrado.R` | Pasa al R Markdown el CSV, la fecha de corte y el nombre del Excel descargable. |
| `combinar_excel_reporte.mjs` | Conserva las hojas del Excel de incidencia y agrega `Inhumación mensual` e `Inhumación detalle`. |
| `probar_pdf_sin_bd.py` | Prueba local del PDF de septiembre de 2026 y crea una vista previa sin cargar PostgreSQL ni publicar. |
| `cargar_septiembre_pruebas.py` | Carga ese PDF solo en `fosas_clandestinas_pruebas`, conservando agosto y deteniéndose si septiembre ya existe. |
| `reporte_mensual_generado_AAAA_MM.html` | Resultado local de cada corte. Se puede abrir o enviar para revisión; no es el archivo que se edita a mano ni se incluye en Git. |

Hay copias anteriores del HTML y un Excel de trabajo en este directorio. Se conservan localmente, pero no son necesarios para ejecutar el generador.

El código que descarga el PDF, lo transforma y lo carga a PostgreSQL está en **otro repositorio**, `ETL-SIEEJ`, dentro de `core/pipelines/fosas_clandestinas/`. Este proyecto no sustituye ese ETL.

## Flujo de datos

```text
PDF oficial → ETL-SIEEJ → PostgreSQL local
                              ↓
              vwm_fosas_clandestinas_mensual
                              ↓
              generar_tabla_desde_bd.py
                              ↓
              HTML + Excel generado → revisión → publicación manual del sitio
```

Cada PDF contiene un registro completo, no únicamente los casos nuevos del mes. La vista mensual usa **solo la publicación más reciente** para evitar sumar varias veces los mismos registros. Agrupa por `fecha_inicio`, es decir, el mes de inicio de procesamiento.

Para mostrar la tabla se omite únicamente el periodo `oct-18` del sitio especial `consecutivo = 0` cuando carece de cifra de víctimas. Sus otros periodos, diciembre de 2018 y enero de 2019, sí se conservan. El generador comprueba primero que la vista coincida con los datos cargados y aplica esta exclusión solo a las filas del HTML; no modifica la vista ni la base.

**Precisión metodológica:** la columna `sitios_inhumacion_clandestina` de la vista se calcula con `COUNT(*)`. Por tanto cuenta renglones o periodos de procesamiento; un sitio con varios periodos puede aparecer más de una vez. Antes de llamar a esa cifra “sitios únicos” o automatizar su publicación, el equipo debe confirmar que esa definición es la deseada.

## Reproducir la generación local

Requisitos: Windows PowerShell, PostgreSQL con la base de pruebas ya cargada y Python con `psycopg2` instalado. En la configuración actual se usa el entorno virtual de `ETL-SIEEJ`.

Con este repositorio y `ETL-SIEEJ` como carpetas hermanas, desde `ETL-SIEEJ`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_tabla_desde_bd.py
```

El programa pide la contraseña de PostgreSQL sin mostrarla. No la escribas en el código ni la guardes en Git. También acepta `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` como variables de entorno. Por seguridad, el script actual **solo admite** `DB_NAME=fosas_clandestinas_pruebas`.

Si el archivo de salida ya existe, el programa se detiene para no sobrescribirlo. Tras revisar que quieres reemplazarlo:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_tabla_desde_bd.py --reemplazar
```

El generador comprueba que la suma mensual de renglones y víctimas coincide con la última publicación cargada. Produce `reporte_mensual_generado_AAAA_MM.html`. Las gráficas, sus cálculos y las demás secciones del HTML permanecen como en la plantilla; **no se actualizan desde esta base**.

Para probar únicamente la lectura del nuevo PDF y el aspecto de la tabla, sin contraseña ni cambios en la base, ejecutar desde `ETL-SIEEJ`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\probar_pdf_sin_bd.py
```

La prueba de septiembre genera `vista_previa_sin_bd_2026_09_sin_oct18.html`; no demuestra aún la carga de ese corte a PostgreSQL.

Para cargar septiembre en la base local de pruebas, desde `ETL-SIEEJ`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\cargar_septiembre_pruebas.py
```

El script pide la contraseña, verifica que la base sea `fosas_clandestinas_pruebas` y que agosto ya esté cargado, carga septiembre sin borrar agosto y actualiza la vista mensual. Si septiembre ya existe, se detiene para no reemplazarlo. Después se puede ejecutar `generar_tabla_desde_bd.py` para producir el HTML del nuevo corte. Ninguno de estos dos programas publica el sitio.

## Generar también el Excel descargable

Cuando llegue el Excel de incidencia correspondiente al reporte, pásalo explícitamente al nuevo generador. No se reutiliza automáticamente un archivo del mes anterior:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\ETL-SIEEJ
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_reporte_con_excel.py --excel-incidencia "C:\ruta\al\Excel-de-incidencia-del-mes.xlsx"
```

Además de Python con `psycopg2`, esta opción necesita Node.js y `@oai/artifact-tool` disponible para `combinar_excel_reporte.mjs`. En esta computadora se usa el runtime de Codex mediante un `node_modules` local que está excluido de Git. En otra computadora o en GitLab habrá que proporcionar esa dependencia antes de ejecutar el comando.

El resultado queda en `reporte_nuevo_para_enviar/reporte_generado_AAAA_MM/` y contiene `reporte_mensual_AAAA_MM.html` y `reporte_mensual_AAAA_MM.xlsx`; `AAAA_MM` indica el corte de inhumación. El botón «Descargar reporte del mes» del HTML enlaza al Excel por nombre relativo; **mantén ambos archivos en la misma carpeta al compartirlos o publicarlos**. El Excel conserva las hojas originales de incidencia y agrega `Inhumación mensual` e `Inhumación detalle` desde la última publicación en PostgreSQL. No modifica ni el Excel de entrada ni la plantilla HTML.

### Opción con el R Markdown fuente

El archivo `reporte_mensual_integrado.Rmd` ya usa el CSV mensual que produce Python, en lugar del antiguo `fosas.csv`. También usa un enlace al Excel del paquete y coloca la tabla en la posición acordada. Para intentar generar **todo el HTML desde R Markdown**, añade `--usar-rmd` al comando anterior. Si `Rscript` no está en PATH, añade `--rscript "C:\ruta\a\Rscript.exe"`. El paquete generado también guardará `tabla_inhumacion.csv` para revisión. Sin `--usar-rmd`, se mantiene el método anterior, que actualiza la tabla en una copia del HTML estático.

**Aún no se ha probado el render completo en esta computadora.** No se encontró Rscript y el Rmd original conserva rutas absolutas de otra Mac (`/Users/gobierno.seguridad/...`) para `data_prueba.rds`, `homicidio.csv`, la población y el shapefile. También faltan recursos relativos como `style_sin.css` y varias imágenes. Esos insumos deben proporcionarse y adaptarse a rutas locales antes de que `--usar-rmd` pueda producir el reporte. El Python actualiza solo inhumación: los datos y cálculos de las demás gráficas siguen siendo responsabilidad del Rmd y sus fuentes. Ni esta opción ni la anterior publican el sitio.

Si ya existe un paquete con ese corte, el programa se detiene. `--reemplazar` permite regenerarlo después de revisar que sea lo deseado. El sitio público y las demás gráficas no cambian automáticamente. Antes de publicar, confirma que el Excel de incidencia corresponde al periodo autorizado y que las cifras de la base fueron aprobadas.

## Revisión antes de publicar

1. Confirmar que el PDF corresponde al corte esperado y que el ETL terminó sin errores.
2. Revisar en PostgreSQL la última `fecha_corte`, los renglones y la vista mensual.
3. Ejecutar el generador y abrir el HTML resultante en un navegador.
4. Comparar cifras y título con la fuente oficial; documentar cualquier corrección manual del PDF.
5. Obtener aprobación de la persona responsable de las cifras.
6. Publicar el HTML validado en el sitio y verificar el enlace público.

**No publicar automáticamente** solo porque el script terminó bien. En este momento el paso de aprobación y publicación es manual.

## Qué falta decidir con el equipo

- Si la cifra oficial de “número de sitios” debe contar periodos (`COUNT(*)`) o sitios únicos.
- Quién valida y autoriza cada corte, y cómo se registrará esa aprobación.
- Si se publicará un HTML nuevo cada mes o si hará falta una API. Una API no es necesaria para actualizar mensualmente un reporte estático.
- Dónde estarán PostgreSQL y las credenciales de producción. La base local de pruebas no debe exponerse en internet.
- Cómo se regenerarán las demás gráficas: ya se obtuvo una copia del R Markdown, pero faltan sus insumos, recursos y entorno R para ejecutarlo localmente.
- Qué archivos deben formar parte del futuro repositorio y quién tendrá acceso de escritura/publicación.

## Preparación del futuro repositorio

Este repositorio es **separado** de `ETL-SIEEJ`. El `.gitignore` evita añadir salidas generadas, respaldos, contraseñas y entornos locales. Antes de cada commit, revisar `git status` y comprobar que no aparezcan datos sensibles. No se ha creado ni publicado un repositorio remoto.

# Reporte mensual: tabla y descarga de sitios de inhumación clandestina

Este repositorio local contiene el reporte HTML y un generador para actualizar la tabla mensual de inhumación con datos de PostgreSQL. También puede preparar, en un solo paso, el HTML y el Excel descargable con las dos hojas de inhumación. Todavía no es una publicación automática.

## Estado actual

- Fuente oficial: [Registro Estatal de Fosas Clandestinas de Jalisco](https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/registro-estatal-de-fosas-clandestinas/).
- Cortes probados: agosto, septiembre y octubre de 2026. Octubre se cargó en la base de pruebas con el comando local automático y se generó un HTML local con la tabla actualizada; el sitio público no cambió.
- Base usada: `fosas_clandestinas_pruebas`, en PostgreSQL local.
- Septiembre: 265 renglones extraídos; 264 incluidos en la tabla después de omitir el periodo `oct-18` sin cifra; 86 meses visibles.
- Sitio publicado: [reporte mensual](https://reporte-mensual-inhumacion-jalisco.alive-fawn-1254.chatgpt.site/). Es una copia estática: no se conecta a PostgreSQL cuando alguien la visita.

## Archivos principales

| Archivo | Para qué sirve |
| --- | --- |
| `reporte_mensual_con_tabla.html` | Plantilla del reporte completo. La tabla de inhumación está entre la comparativa de delitos contra la vida y el mapa de tasas delictivas; conserva las demás gráficas y contenido. |
| `generar_tabla_desde_bd.py` | Lee la última publicación de la base de pruebas, verifica los totales y sustituye el título y las filas de la tabla. |
| `actualizar_graficas_desde_html.mjs` | Toma nueve gráficas y las 16 filas de la tabla de delitos de un HTML mensual nuevo, conservando los textos corregidos y la tabla de inhumación. |
| `generar_reporte_con_excel.py` | Recibe el Excel de incidencia del mes, consulta la última publicación de inhumación y genera juntos el HTML y el Excel combinado. |
| `reporte_mensual_integrado.Rmd` | Copia del R Markdown recibido; reemplaza la tabla antigua de fosas por el CSV mensual preparado por Python y coloca la tabla entre la comparativa de vida y el mapa. |
| `renderizar_reporte_integrado.R` | Pasa al R Markdown el CSV, la fecha de corte y el nombre del Excel descargable. |
| `combinar_excel_reporte.mjs` | Conserva las hojas del Excel de incidencia y agrega únicamente `Sitios de inhumación`. |
| `probar_pdf_sin_bd.py` | Prueba local del PDF de septiembre de 2026 y crea una vista previa sin cargar PostgreSQL ni publicar. |
| `cargar_septiembre_pruebas.py` | Carga ese PDF solo en `fosas_clandestinas_pruebas`, conservando agosto y deteniéndose si septiembre ya existe. |
| `actualizar_fosas_local.py` | Alternativa local para validar y cargar un PDF ya descargado. Reutiliza la transformación y carga de `ETL-SIEEJ`, sin su descubrimiento automático. |
| `actualizar_fosas_automatico_local.py` | Descubre y descarga el PDF oficial con el extractor de `ETL-SIEEJ`, lo transforma y, con `--cargar`, lo carga en la base local de pruebas. No requiere Airflow. |
| `reporte_mensual_generado_AAAA_MM.html` | Resultado local de cada corte. Se puede abrir o enviar para revisión; no es el archivo que se edita a mano ni se incluye en Git. |

Hay copias anteriores del HTML y un Excel de trabajo en este directorio. Se conservan localmente, pero no son necesarios para ejecutar el generador.

El código que descubre y descarga el PDF, lo transforma y lo carga a PostgreSQL está en **otro repositorio**, `ETL-SIEEJ`, dentro de `core/pipelines/fosas_clandestinas/`. Su DAG está en `dags/etl_fosas_clandestinas.py`. Este proyecto no sustituye ese ETL. Consulta [FLUJO_ETL_Y_REPORTE.md](FLUJO_ETL_Y_REPORTE.md) para conocer el recorrido completo y la alternativa local.

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

### Secuencia mensual para repetir el trabajo

1. Recibir el HTML actualizado de incidencia y comprobar su fecha de corte.
2. Ejecutar `actualizar_fosas_automatico_local.py --corte AAAA-MM` para descubrir, descargar y validar el PDF oficial sin modificar PostgreSQL. Comparar la URL y las cifras con la fuente.
3. Ejecutar el mismo comando con `--cargar` para guardar el nuevo corte en `fosas_clandestinas_pruebas`. Revisar el corte, los renglones y los meses que informa al terminar.
4. Desde `reporte_nuevo_para_enviar`, ejecutar `node .\actualizar_graficas_desde_html.mjs --nuevo "C:\ruta\al\HTML-recibido.html" --salida .\reporte_mensual_con_graficas_AAAA_MM.html`. Ese archivo es un borrador: aún contiene la tabla de inhumación anterior.
5. Desde `ETL-SIEEJ`, ejecutar `.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_tabla_desde_bd.py --plantilla ..\reporte_nuevo_para_enviar\reporte_mensual_con_graficas_AAAA_MM.html`. El resultado es `reporte_mensual_generado_AAAA_MM.html`.
6. Recibir el Excel de incidencia del mismo mes. Para generar juntos el HTML y el Excel combinado desde PostgreSQL, ejecutar `generar_reporte_con_excel.py --excel-incidencia "C:\ruta\al\Excel-del-mes.xlsx" --plantilla "C:\ruta\al\borrador-con-graficas.html"`. El Excel conserva las hojas de incidencia y agrega `Sitios de inhumación`; no incluye `Inhumación detalle`.
7. Revisar las fechas, gráficas, tabla, hojas y enlaces de ambos archivos. Publicar solo por el procedimiento autorizado del equipo.

Sustituye `AAAA-MM` por el corte del PDF, `AAAA_MM` por el mismo año y mes con guion bajo y la ruta de ejemplo por el HTML recibido. Los borradores y reportes generados están excluidos de Git; el repositorio guarda los programas, la plantilla y esta documentación.

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

### Incorporar las gráficas y la tabla de delitos de un HTML mensual nuevo

Cuando recibas el HTML nuevo, desde la carpeta `reporte_nuevo_para_enviar` ejecuta:

```powershell
node .\actualizar_graficas_desde_html.mjs --nuevo "C:\ruta\al\reporte_nuevo.html"
```

El programa crea `reporte_mensual_con_graficas_nuevas.html` y **no sobrescribe** la plantilla ni el HTML recibido. Copia tres gráficas Plotly, cinco imágenes de gráficas, el mapa Leaflet y las seis columnas de valores e indicadores de cada uno de los 16 delitos. Conserva nuestros nombres corregidos, encabezados y grupos de la tabla. Al copiar las tres Plotly, elimina las series de promedios con líneas punteadas y los títulos redundantes de los ejes. Si el mapa usa `Esri.WorldGrayCanvas`, convierte esa capa a su URL de teselas equivalente para que el HTML no dependa de un complemento Leaflet adicional; otros proveedores desconocidos detienen el proceso. También toma la fecha de corte del HTML recibido, traduce el mes al español (por ejemplo, `30 de September de 2026` → `30 de septiembre de 2026`) y actualiza la introducción, las fechas de las secciones de gráficas y el encabezado `Cifras de septiembre de 2026`. Conserva intacta la tabla de inhumación. Se detiene si no reconoce alguna sección, las 16 filas o la fecha de corte. Si ya existe el borrador, debes revisarlo antes de repetir con `--reemplazar`.

Este es **solo un borrador**: la tabla de inhumación y el enlace al Excel pueden seguir correspondiendo al mes anterior. Las imágenes estáticas y el mapa conservan el estilo del HTML recibido; únicamente se quitan las líneas punteadas de las tres Plotly. Antes de publicar, hay que actualizar y validar los datos con la fuente oficial. No se recalculan las gráficas ni las cifras de los 16 delitos a partir del HTML: se copian tal como llegaron.

Si ya generaste el reporte con una versión anterior del programa, `limpiar_lineas_plotly.mjs` puede crear una copia sin las líneas punteadas sin volver a consultar PostgreSQL:

```powershell
node .\limpiar_lineas_plotly.mjs .\reporte_mensual_generado_2026_09.html .\reporte_mensual_generado_2026_09_sin_lineas.html
```

Tras revisar el borrador, puedes usarlo como base para generar la tabla de inhumación actualizada:

```powershell
.\..\ETL-SIEEJ\.venv\Scripts\python.exe .\generar_tabla_desde_bd.py --plantilla .\reporte_mensual_con_graficas_nuevas.html
```

El generador del paquete HTML + Excel también acepta `--plantilla .\reporte_mensual_con_graficas_nuevas.html`. Ninguno de estos comandos actualiza por sí solo el resto de las tablas del informe ni publica el sitio.

Para probar únicamente la lectura del nuevo PDF y el aspecto de la tabla, sin contraseña ni cambios en la base, ejecutar desde `ETL-SIEEJ`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\probar_pdf_sin_bd.py
```

La prueba de septiembre genera `vista_previa_sin_bd_2026_09_sin_oct18.html`; no demuestra aún la carga de ese corte a PostgreSQL.

### Actualizar desde la fuente oficial sin Airflow

Desde `ETL-SIEEJ`, indica el corte esperado. El programa busca el PDF en el índice oficial, lo descarga y transforma; sin `--cargar` no escribe en PostgreSQL:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\ETL-SIEEJ
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10
```

Comprueba la URL y las cifras mostradas con la publicación oficial. Después, para cargar ese corte en `fosas_clandestinas_pruebas`, repite con `--cargar`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10 --cargar
```

El programa comprueba la base y rechaza cortes ya cargados o anteriores. Pide la contraseña sin mostrarla. No genera ni publica el HTML: ese es el paso posterior. **Estado de prueba:** en la computadora del usuario, el comando descubrió y descargó el PDF oficial de octubre de 2026; cargó 266 renglones y refrescó la vista con 88 meses. Son 261 sitios numerados y un registro especial sin número (`oct-18`) con tres periodos. La verificación posterior confirmó el corte y los renglones en PostgreSQL. Después se recibió el HTML mensual de octubre, se incorporaron nueve gráficas y las 16 filas de delitos, y se generó `reporte_mensual_generado_2026_10.html`. Su tabla de inhumación tiene 87 meses y 265 renglones/periodos tras omitir el periodo `oct-18` sin cifra. El sitio público no cambió.

### Alternativa local: cargar un PDF descargado

El paquete `core.pipelines.fosas_clandestinas` no tiene `__main__.py`: la instrucción `python -m core.pipelines.fosas_clandestinas update` del README del ETL no funciona en esta copia. El DAG `etl_fosas_clandestinas_update` de Airflow define el flujo automático completo. `actualizar_fosas_local.py` es una alternativa sin Airflow: recibe un PDF ya descargado y ejecuta la transformación y carga del mismo ETL; no descarga el PDF. **Primero valida sin escribir en PostgreSQL**:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\ETL-SIEEJ
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_local.py --pdf "C:\ruta\al\PDF-oficial.pdf" --corte 2026-10 --url "https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/wp-content/uploads/2026/11/archivo.pdf"
```

Los nombres y fechas del ejemplo son ilustrativos: sustituye la ruta, el corte y la URL por los de la nueva publicación. Revisa que los renglones y sitios informados coincidan con el PDF. Después, **solo si ya lo verificaste**, repite el mismo comando agregando `--cargar`. Pedirá la contraseña sin mostrarla, comprobará que la conexión apunte a `fosas_clandestinas_pruebas` en la computadora local, rechazará un corte ya cargado o anterior y actualizará la vista mensual. El Excel y el HTML se generan después; este comando no publica el sitio. El campo `modificado` de esta carga manual usa la fecha local del PDF, no la fecha de modificación publicada en el servidor.

El cargador antiguo, limitado a septiembre de 2026, se conserva como antecedente. Para repetir esa prueba histórica, desde `ETL-SIEEJ`:

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

El resultado queda en `reporte_nuevo_para_enviar/reporte_generado_AAAA_MM/` y contiene `reporte_mensual_AAAA_MM.html` y `plataforma_seguridad_al_DD_MM_AAAA.xlsx`, donde `DD_MM_AAAA` es el último día y el número de mes del corte de inhumación; por ejemplo, `plataforma_seguridad_al_31_10_2026.xlsx`. Para conservar las gráficas del mes recibido, pasa explícitamente `--plantilla` con el borrador generado por `actualizar_graficas_desde_html.mjs`; el valor por defecto puede contener gráficas anteriores. El botón «Descargar reporte del mes» del HTML abre la página oficial de reportes del IIEG y el botón «Datos abiertos» abre el repositorio oficial de datos: ninguno descarga directamente este Excel. El Excel se genera como archivo local separado, conserva las hojas originales de incidencia y agrega únicamente la pestaña `Sitios de inhumación`, cuyo título interno también dice `Sitios de inhumación`. No modifica ni el Excel de entrada ni la plantilla HTML.

**Paquete de octubre de 2026:** se preparó una copia local en `outputs/01a07d7c-c08b-7883-8b40-150c16819dee/reporte_octubre_2026/` con el HTML generado y el Excel combinado. El Excel de entrada fue `Incidencia Delictiva mensual octubre 2026 valores.xlsx`; se conservaron `NOTA`, `ESTADO`, `AMG` e `INTERIOR` y se agregó `Sitios de inhumación` con los 87 meses visibles del HTML. No se agregó `Inhumación detalle`. Este paquete no se publicó ni se incluye en Git.

### Opción con el R Markdown fuente

El archivo `reporte_mensual_integrado.Rmd` ya usa el CSV mensual que produce Python, en lugar del antiguo `fosas.csv`. También incluye los dos enlaces oficiales y coloca la tabla en la posición acordada. Para intentar generar **todo el HTML desde R Markdown**, añade `--usar-rmd` al comando anterior. Si `Rscript` no está en PATH, añade `--rscript "C:\ruta\a\Rscript.exe"`. El paquete generado también guardará `tabla_inhumacion.csv` para revisión. Sin `--usar-rmd`, se mantiene el método anterior, que actualiza la tabla en una copia del HTML estático.

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

## Repositorio GitLab

Este repositorio es **separado** de `ETL-SIEEJ`. Su remoto `origin` apunta al proyecto GitLab `plataforma-de-seguridad_generacion-de-tabla-de-inhumaciones`. El `.gitignore` evita añadir salidas generadas, respaldos, contraseñas y entornos locales. Antes de cada commit, revisar `git status` y comprobar que no aparezcan datos sensibles. Los reportes HTML y Excel generados para cada mes se entregan como archivos separados: no se incluyen en Git.

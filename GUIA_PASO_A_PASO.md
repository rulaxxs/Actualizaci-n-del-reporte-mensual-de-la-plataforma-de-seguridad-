# Cómo usar este repositorio cada mes

Este proyecto prepara una copia del reporte mensual HTML y un Excel con la tabla de sitios de inhumación. El ETL que obtiene el PDF de Fiscalía vive en el repositorio hermano `ETL-SIEEJ`. La base usada en las pruebas es `fosas_clandestinas_pruebas`, en PostgreSQL local. Ninguno de los comandos publica el sitio web.

## 1. Preparar las carpetas una sola vez

En la computadora de trabajo, `ETL-SIEEJ` y este repositorio deben estar dentro de la misma carpeta. El programa local busca el ETL en `../ETL-SIEEJ`.

```text
defunciones/
├── ETL-SIEEJ/
└── reporte_nuevo_para_enviar/   ← este repositorio en la computadora actual
```

En otra computadora puedes clonar este proyecto por HTTPS, porque el acceso SSH requiere registrar una clave en GitHub:

```powershell
git clone https://github.com/rulaxxs/Actualizaci-n-del-reporte-mensual-de-la-plataforma-de-seguridad-.git reporte_nuevo_para_enviar
```

También se necesita `ETL-SIEEJ` como carpeta hermana, su entorno Python `.venv`, PostgreSQL con las tablas y la vista del ETL, el catálogo de municipios y Node.js. La configuración y las contraseñas no se guardan en Git. En esta computadora esos elementos ya se prepararon. El Excel combinado usa `@oai/artifact-tool` mediante el runtime local de Codex; en otra computadora habrá que proporcionar esa dependencia antes de ejecutar la combinación.

## 2. Actualizar el código antes de empezar

Desde PowerShell, entra a este repositorio y trae los cambios de GitHub:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\reporte_nuevo_para_enviar
git pull github main
```

Ese comando corresponde a esta computadora, donde `github` es el segundo remoto y `origin` es GitLab. Si clonaste desde GitHub en otra computadora, usa `git pull origin main`. `git remote -v` muestra los nombres disponibles.

## 3. Descargar y validar el nuevo PDF mediante el ETL

Entra a `ETL-SIEEJ`. Sustituye `2026-10` por el corte que corresponda al nuevo PDF oficial. Primero ejecuta **sin** `--cargar`:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\ETL-SIEEJ
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10
```

El comando busca y descarga el PDF de Fiscalía, muestra su URL y extrae las cifras. Comprueba que el corte y los renglones correspondan al PDF. Sin `--cargar` no cambia PostgreSQL. Un PDF reemite el registro completo; no contiene solo los casos nuevos.

## 4. Cargar el corte en PostgreSQL local

Después de revisar la validación, repite con `--cargar`:

```powershell
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\actualizar_fosas_automatico_local.py --corte 2026-10 --cargar
```

Escribe la contraseña cuando la pida. El programa solo admite la base local `fosas_clandestinas_pruebas`, rechaza un corte ya cargado y comprueba al terminar el corte, los renglones y la vista mensual. No compartas la contraseña ni la guardes en el repositorio.

## 5. Recibir el HTML y el Excel de incidencia del mes

Se necesitan dos archivos del mismo periodo:

- El HTML mensual nuevo, con las gráficas y la tabla de delitos actualizadas.
- El Excel de incidencia del mes, cuyas hojas originales se conservarán.

El PDF de Fiscalía sirve para la tabla de inhumación. No sustituye esos dos archivos de incidencia.

## 6. Incorporar las gráficas del HTML recibido

Desde este repositorio, cambia la ruta del ejemplo por la ubicación del HTML recibido. Usa el año y mes del reporte en el nombre del borrador:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\reporte_nuevo_para_enviar
node .\actualizar_graficas_desde_html.mjs --nuevo "C:\ruta\reporte_recibido.html" --salida .\reporte_mensual_con_graficas_2026_10.html
```

El resultado es un borrador con las gráficas, el mapa, las 16 filas de delitos y la fecha del HTML recibido. Todavía contiene la tabla de inhumación anterior. El programa no sobrescribe el HTML recibido ni la plantilla.

## 7. Crear el paquete HTML y Excel

Desde `ETL-SIEEJ`, indica el Excel recibido y el borrador del paso anterior:

```powershell
cd C:\Users\raul\Documents\ChatGPT\defunciones\ETL-SIEEJ
.\.venv\Scripts\python.exe ..\reporte_nuevo_para_enviar\generar_reporte_con_excel.py --excel-incidencia "C:\ruta\Incidencia_del_mes.xlsx" --plantilla ..\reporte_nuevo_para_enviar\reporte_mensual_con_graficas_2026_10.html
```

El programa lee la última publicación de PostgreSQL y crea `reporte_nuevo_para_enviar/reporte_generado_2026_10/` con:

- `reporte_mensual_2026_10.html`: gráficas del HTML recibido y tabla de inhumación del último corte de la base.
- `plataforma_seguridad_al_31_10_2026.xlsx`: hojas originales de incidencia más `Sitios de inhumación`.

El nombre del Excel usa el último día del mes, el número de mes y el año. Si el paquete ya existe, el programa se detiene; usa `--reemplazar` solo después de revisar el archivo existente. El botón «Descargar reporte del mes» del HTML lleva a la página de reportes del IIEG; no descarga este Excel directamente.

## 8. Revisar y entregar

Abre el HTML y el Excel. Revisa la fecha, gráficas, mapa, cifras, las cinco hojas del Excel y el nombre de la pestaña `Sitios de inhumación`. En el corte de octubre de 2026, la base contiene 266 renglones, mientras la tabla publicada muestra 265 periodos y 87 meses porque omite `oct-18` sin cifra. Ese ajuste está en el generador y no borra datos de PostgreSQL.

Entrega los archivos finales a quien revise y publique el reporte. Los archivos generados están excluidos de Git: **subir este repositorio actualiza el código y la documentación, no la página pública ni los reportes mensuales ya generados**.

## 9. Guardar cambios de código en Git

Este paso solo se usa cuando cambias programas, plantilla o documentación. Desde la carpeta del repositorio:

```powershell
git status
git add README.md GUIA_PASO_A_PASO.md
git commit -m "Actualizar instrucciones del reporte"
git push github main
git push origin main
```

Antes de `git add`, comprueba con `git status` que no estás agregando contraseñas ni archivos de trabajo. En esta computadora, `github` apunta a tu repositorio personal y `origin` al GitLab institucional. Si clonaste desde GitHub, `origin` será GitHub y quizá no exista un segundo remoto. No ejecutes `git add` ni `git commit` si no cambiaste el código o la documentación.

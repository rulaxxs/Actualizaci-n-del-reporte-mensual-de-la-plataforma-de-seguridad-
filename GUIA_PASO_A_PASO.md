# Cómo usar este repositorio cada mes

Este proyecto prepara una copia del reporte mensual HTML y un Excel con la tabla de sitios de inhumación. El ETL que obtiene el PDF de Fiscalía vive en el repositorio hermano [ETL-SIEEJ](https://github.com/iieg-oficial/ETL-SIEEJ). La base usada en las pruebas es `fosas_clandestinas_pruebas`, en PostgreSQL local. Ninguno de los comandos publica el sitio web.

## 1. Preparar las carpetas una sola vez

En la computadora de trabajo, `ETL-SIEEJ` y este repositorio deben estar dentro de la misma carpeta. Puedes llamar a esa carpeta principal `reporte_plataforma_de_seguridad` y guardarla donde prefieras. El programa busca el ETL en `../ETL-SIEEJ` respecto a este repositorio; no depende del nombre de usuario ni de una ruta absoluta.

```text
reporte_plataforma_de_seguridad/
├── ETL-SIEEJ/
└── reporte_nuevo_para_enviar/
    ├── README.md
    ├── GUIA_PASO_A_PASO.md
    ├── reportes_generados/       ← salidas locales; no se suben a Git
    │   └── 2026_10/
    │       ├── reporte_mensual_2026_10.html
    │       └── plataforma_seguridad_al_31_10_2026.xlsx
    └── otros programas y plantilla
```

En otra computadora, crea la carpeta principal y clona este proyecto por HTTPS. Si ya tienes `ETL-SIEEJ`, colócalo como carpeta hermana; no necesitas volver a clonarlo:

```sh
mkdir reporte_plataforma_de_seguridad
cd reporte_plataforma_de_seguridad
git clone https://github.com/rulaxxs/Actualizaci-n-del-reporte-mensual-de-la-plataforma-de-seguridad-.git reporte_nuevo_para_enviar
git clone https://github.com/iieg-oficial/ETL-SIEEJ.git ETL-SIEEJ
```

También se necesita `ETL-SIEEJ` como carpeta hermana, su entorno Python `.venv`, PostgreSQL con las tablas y la vista del ETL, el catálogo de municipios y Node.js para copiar las gráficas del HTML. Si aún no tienes las bases locales, sigue [CONFIGURAR_POSTGRESQL.md](CONFIGURAR_POSTGRESQL.md). Prepara `.venv` con las dependencias indicadas por `ETL-SIEEJ`. La configuración y las contraseñas no se guardan en Git.

Para usar los mismos comandos mensuales en cualquier sistema, activa el entorno Python del ETL. En **Windows (PowerShell)**:

```powershell
cd ETL-SIEEJ
.\.venv\Scripts\Activate.ps1
```

En **macOS o Linux (bash/zsh)**:

```sh
cd ETL-SIEEJ
source .venv/bin/activate
```

Si la terminal de Windows impide activar el entorno, usa `.\.venv\Scripts\python.exe` en lugar de `python` en los comandos siguientes. Ya con el entorno activo, instala una vez `openpyxl` para combinar el Excel:

```sh
python -m pip install -r ../reporte_nuevo_para_enviar/requirements_excel.txt
```

El combinador se detiene si un Excel nuevo contiene gráficos, objetos, tablas dinámicas, vínculos externos, macros o fórmulas que requieren revisión antes de guardar una copia.

## 2. Actualizar el código antes de empezar

Desde la terminal, entra a este repositorio y trae los cambios de GitHub:

```sh
cd ../reporte_nuevo_para_enviar
git pull origin main
```

Si clonaste desde GitHub, `origin` apunta a GitHub. `git remote -v` muestra a qué servidor apunta cada remoto.

## 3. Descargar y validar el nuevo PDF mediante el ETL

Entra a `ETL-SIEEJ`. Sustituye `2026-10` por el corte que corresponda al nuevo PDF oficial. Primero ejecuta **sin** `--cargar`:

```sh
cd ../ETL-SIEEJ
python ../reporte_nuevo_para_enviar/actualizar_fosas_automatico_local.py --corte 2026-10
```

El comando busca y descarga el PDF de Fiscalía, muestra su URL y extrae las cifras. Comprueba que el corte y los renglones correspondan al PDF. Sin `--cargar` no cambia PostgreSQL. Un PDF reemite el registro completo; no contiene solo los casos nuevos.

## 4. Cargar el corte en PostgreSQL local

Después de revisar la validación, repite con `--cargar`:

```sh
python ../reporte_nuevo_para_enviar/actualizar_fosas_automatico_local.py --corte 2026-10 --cargar
```

Escribe la contraseña cuando la pida. El programa solo admite la base local `fosas_clandestinas_pruebas`, rechaza un corte ya cargado y comprueba al terminar el corte, los renglones y la vista mensual. No compartas la contraseña ni la guardes en el repositorio.

## 5. Recibir el HTML y el Excel de incidencia del mes

Se necesitan dos archivos del mismo periodo:

- El HTML mensual nuevo, con las gráficas y la tabla de delitos actualizadas.
- El Excel de incidencia del mes, cuyas hojas originales se conservarán.

El PDF de Fiscalía sirve para la tabla de inhumación. No sustituye esos dos archivos de incidencia.

## 6. Incorporar las gráficas del HTML recibido

Desde este repositorio, cambia la ruta del ejemplo por la ubicación del HTML recibido. Usa el año y mes del reporte en el nombre del borrador:

```sh
cd ../reporte_nuevo_para_enviar
node actualizar_graficas_desde_html.mjs --nuevo "/ruta/al/reporte_recibido.html" --salida reporte_mensual_con_graficas_2026_10.html
```

Sustituye `/ruta/al/reporte_recibido.html` por la ruta real. En Windows también puedes usar, por ejemplo, `"C:/ruta/reporte_recibido.html"`. El resultado es un borrador con las gráficas, el mapa, las 16 filas de delitos y la fecha del HTML recibido. Todavía contiene la tabla de inhumación anterior. El programa no sobrescribe el HTML recibido ni la plantilla.

## 7. Crear el paquete HTML y Excel

Desde `ETL-SIEEJ`, indica el Excel recibido y el borrador del paso anterior:

```sh
cd ../ETL-SIEEJ
python ../reporte_nuevo_para_enviar/generar_reporte_con_excel.py --excel-incidencia "/ruta/al/Incidencia_del_mes.xlsx" --plantilla ../reporte_nuevo_para_enviar/reporte_mensual_con_graficas_2026_10.html
```

Sustituye también la ruta del Excel por la real; en Windows puedes usar `"C:/ruta/Incidencia_del_mes.xlsx"`. El programa lee la última publicación de PostgreSQL y crea `reporte_nuevo_para_enviar/reportes_generados/2026_10/` con:

- `reporte_mensual_2026_10.html`: gráficas del HTML recibido y tabla de inhumación del último corte de la base.
- `plataforma_seguridad_al_31_10_2026.xlsx`: hojas originales de incidencia más `Sitios de inhumación`.

El nombre del Excel usa el último día del mes, el número de mes y el año. El programa crea una carpeta nueva `AAAA_MM` para cada corte: por ejemplo, noviembre se guardará en `reportes_generados/2026_11/`, sin borrar octubre. Si el paquete ya existe, el programa se detiene; usa `--reemplazar` solo después de revisar el archivo existente. El botón «Descargar reporte del mes» del HTML lleva a la página de reportes del IIEG; no descarga este Excel directamente.

## 8. Revisar y entregar

Abre el HTML y el Excel. Revisa la fecha, gráficas, mapa, cifras, las cinco hojas del Excel y el nombre de la pestaña `Sitios de inhumación`. En el corte de octubre de 2026, la base contiene 266 renglones, mientras la tabla publicada muestra 265 periodos y 87 meses porque omite `oct-18` sin cifra. Ese ajuste está en el generador y no borra datos de PostgreSQL.

Entrega los archivos finales a quien revise y publique el reporte. Los archivos generados están excluidos de Git: **subir este repositorio actualiza el código y la documentación, no la página pública ni los reportes mensuales ya generados**.

## 9. Guardar cambios de código en Git

Este paso solo se usa cuando cambias programas, plantilla o documentación. Vuelve a la carpeta del repositorio:

```sh
cd ../reporte_nuevo_para_enviar
git status
git add README.md GUIA_PASO_A_PASO.md
git commit -m "Actualizar instrucciones del reporte"
git push origin main
```

Antes de `git add`, comprueba con `git status` que no estás agregando contraseñas ni archivos de trabajo. Si también tienes configurado un remoto institucional llamado `gitlab`, puedes ejecutar `git push gitlab main`. No ejecutes `git add` ni `git commit` si no cambiaste el código o la documentación.

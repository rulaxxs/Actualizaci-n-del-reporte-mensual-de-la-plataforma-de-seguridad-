# Preparar PostgreSQL para las pruebas locales

Esta guía prepara las bases que usa el reporte. Los esquemas y datos iniciales vienen del repositorio oficial [ETL-SIEEJ](https://github.com/iieg-oficial/ETL-SIEEJ). Los comandos se ejecutan desde la carpeta `ETL-SIEEJ` y sirven en Windows, macOS y Linux si `psql`, `createdb` y `flyway` están disponibles en la terminal. También puedes crear las bases desde pgAdmin 4.

## 1. Comprobar los requisitos

Instala PostgreSQL y PostGIS, y comprueba que puedes conectarte a tu servidor local. Para aplicar las migraciones de fosas necesitas Flyway. El ETL debe estar clonado como carpeta hermana de `reporte_nuevo_para_enviar`, según la [guía mensual](GUIA_PASO_A_PASO.md).

```sh
psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c 'SELECT current_database(), version();'
```

PostgreSQL pedirá la contraseña si hace falta. En Windows, si `psql` no se reconoce, puedes usar la **SQL Shell (psql)** instalada con PostgreSQL o añadir su carpeta `bin` al `PATH`.

## 2. Crear dos bases locales

Desde la terminal, crea una base para el catálogo geográfico y otra para las pruebas del reporte:

```sh
createdb -h 127.0.0.1 -p 5432 -U postgres cvegeo_pruebas
createdb -h 127.0.0.1 -p 5432 -U postgres fosas_clandestinas_pruebas
```

En pgAdmin 4, haz clic derecho en **Databases → Create → Database** y crea esos mismos nombres. Si alguna base ya existe, consérvala: no la borres ni repitas su carga inicial sin revisar sus datos.

## 3. Cargar el catálogo de municipios

El archivo `migrations/cvegeo/sql/V1__create_cvegeo.sql` del ETL crea las tablas e incluye los datos geográficos. Requiere PostGIS. Ejecútalo con `psql`, porque contiene bloques `COPY ... FROM stdin`:

```sh
psql -h 127.0.0.1 -p 5432 -U postgres -d cvegeo_pruebas -v ON_ERROR_STOP=1 -f migrations/cvegeo/sql/V1__create_cvegeo.sql
```

Comprueba que están los 125 municipios de Jalisco:

```sh
psql -h 127.0.0.1 -p 5432 -U postgres -d cvegeo_pruebas -c 'SELECT count(*) FROM cvegeo_municipalities WHERE cve_ent = 14;'
```

## 4. Aplicar las migraciones de fosas

En `ETL-SIEEJ/migrations/fosas_clandestinas/`, copia `flyway.conf.example` a `flyway.conf`. Rellena los valores reales sin los corchetes angulares:

| Propiedad | Valor para estas pruebas |
| --- | --- |
| `flyway.url` | `jdbc:postgresql://127.0.0.1:5432/fosas_clandestinas_pruebas` |
| `flyway.user`, `flyway.password` | Usuario local de PostgreSQL y su contraseña |
| `flyway.placeholders.fdw_dbname` | `cvegeo_pruebas` |
| `flyway.placeholders.fdw_host`, `flyway.placeholders.fdw_port` | `127.0.0.1` y `5432` |
| `flyway.placeholders.fdw_user`, `flyway.placeholders.fdw_password` | Usuario y contraseña con acceso a `cvegeo_pruebas` |

Guarda `flyway.conf` solo en tu computadora; contiene contraseñas y no se debe agregar a Git. Revisa que `flyway.locations=migrations/fosas_clandestinas/sql`. Desde la raíz del ETL, aplica las cinco migraciones en orden:

```sh
flyway -configFiles=migrations/fosas_clandestinas/flyway.conf migrate
```

La primera migración crea `postgres_fdw` y la conexión al catálogo; las siguientes crean `cat_publicaciones`, `stg_fosas_clandestinas`, las vistas y `vwm_fosas_clandestinas_mensual`. Flyway registra cuáles ya se aplicaron. No ejecutes `flyway clean`: eliminaría objetos y datos de la base configurada.

## 5. Verificar la conexión entre bases

Conéctate a `fosas_clandestinas_pruebas` desde pgAdmin o `psql` y ejecuta:

```sql
SELECT current_database();
SELECT count(*) FROM cvegeo_municipalities WHERE cve_ent = 14;
SELECT to_regclass('public.cat_publicaciones') AS publicaciones,
       to_regclass('public.stg_fosas_clandestinas') AS registros,
       to_regclass('public.vwm_fosas_clandestinas_mensual') AS vista_mensual;
```

La primera consulta debe devolver `fosas_clandestinas_pruebas`, la segunda `125` y la tercera los tres nombres. Si falla la segunda con **autenticación password falló**, revisa `flyway.placeholders.fdw_password`: la contraseña del `USER MAPPING` es independiente de la conexión inicial de pgAdmin. Después de cambiarla en `flyway.conf`, una migración ya aplicada no actualiza automáticamente el mapeo; corrígelo en PostgreSQL con una contraseña válida sin pegarla en el repositorio.

## 6. Continuar con la guía mensual

Configura el entorno Python de `ETL-SIEEJ` como indica su repositorio y sigue [GUIA_PASO_A_PASO.md](GUIA_PASO_A_PASO.md) para validar el PDF, cargar un corte y generar el HTML y el Excel. Estas bases son **locales de pruebas**. El programa de carga comprueba que la base se llame `fosas_clandestinas_pruebas`.

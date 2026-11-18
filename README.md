# DropX Web

Panel web, sitio público y API del proyecto DropX (mensajería y logística en Cartagena de Indias), desarrollados con Flask, SQLite (desarrollo) y MySQL (producción).
La API es la que utiliza la app móvil [`dropx_app`](https://github.com/yammadev/dropx_app).

## Capturas

### Sitio público

| Inicio | Rastreo | Ser aliado |
|---|---|---|
| ![Inicio](docs/screenshots/sitio-inicio.png) | ![Rastreo](docs/screenshots/sitio-rastreo.png) | ![Ser aliado](docs/screenshots/sitio-ser-aliado.png) |

### Suite

| Dashboard | Paquetes |
|---|---|
| ![Dashboard](docs/screenshots/suite-dashboard.png) | ![Paquetes](docs/screenshots/suite-paquetes.png) |
| **Nuevo paquete** | **Detalle paquete** |
| ![Nuevo paquete](docs/screenshots/suite-nuevo-paquete.png) | ![Detalle paquete](docs/screenshots/suite-detalle.png) |
| **Mapa** | **Repartidores** |
| ![Mapa](docs/screenshots/suite-mapa.png) | ![Repartidores](docs/screenshots/suite-repartidores.png) |
| **Managers** | **Reportes** |
| ![Managers](docs/screenshots/suite-managers.png) | ![Reportes](docs/screenshots/suite-reportes.png) |

## Instalación y prueba

**Requisitos:** Python 3.10 o superior. La base de datos local es un archivo SQLite (`instance/dropx.db`) que se crea solo, así que no hace falta instalar MySQL. No se necesita Node.

Terminal de VS Code, un comando por línea:

```bash
# Montar ambiente virtual e instalar requerimientos
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copiar .env y generar llave aleatoria
cp .env.example .env
flask --app app key:generate
```

Cambiar en el `.env` los nombres (`SEED_*_NAME`) y las contraseñas (`SEED_*_PASSWORD`) y, luego, cargar los datos de prueba y encender el servidor:

```bash
# Datos de prueba y encender
flask --app app db:test
flask --app app run --debug

# Encender en otro puerto (ej. 5001)
flask --app app run --debug --port 5001
```

`db:test` reinicia la base de datos (pide confirmación) y crea los usuarios iniciales, 4 repartidores y 40 paquetes con su historial. Con `--packages 100` cambia la cantidad de paquetes.

El sitio queda en <http://127.0.0.1:5000> y la Suite en <http://127.0.0.1:5000/suite/login>. Las contraseñas son las definidas en el `.env`.

| Usuario | Correo | Rol |
|---|---|---|
| Administrador | `admin@dropx.com` | `admin` |
| Manager | `manager@dropx.com` | `manager` |
| Jhon Doe | `courier@dropx.com` | `courier` |
| Repartidores de prueba | `ana@dropx.com`, `carlos@dropx.com`, `luis@dropx.com`, `maria@dropx.com` | `courier` |

Qué revisar: como `admin` se ven todas las secciones, se puede eliminar y en Reportes se ven y descargan (CSV) los reportes de paquetes y de repartidores; como `manager` no aparecen Managers ni Reportes y no se puede eliminar; al crear un paquete se marcan el origen y el destino en el mapa, y la sección Mapa los muestra; el rastreo público se prueba en <http://127.0.0.1:5000/rastreo> con una guía como `DX-000001`; y la API con Postman, como se explica en [docs/api.md](docs/api.md).

### Comandos

| Comando | Qué hace |
|---|---|
| `flask --app app db:test` | Reinicia la base de datos y crea datos de prueba (solo desarrollo) |
| `flask --app app db:fresh` | Reinicia la base de datos y crea solo los usuarios iniciales (solo desarrollo) |
| `flask --app app db:upgrade` | Crea o actualiza las tablas (aplica las migraciones) |
| `flask --app app db:seed` | Crea los usuarios iniciales (los que ya existen se omiten) |
| `flask --app app db:migrate -m "descripcion"` | Genera una migración nueva al cambiar los modelos |
| `flask --app app key:generate` | Crea la `SECRET_KEY` en el `.env` |

Al cambiar la `SECRET_KEY` se cierran las sesiones y los tokens vigentes.

### Cambiar el diseño (opcional, requiere Node.js)

El CSS (`tailwind.css`), Chart.js y Leaflet ya están generados en el repositorio. Solo si se cambian las clases de las plantillas o los colores de `app/static/css/input.css`, se vuelven a generar:

```bash
npm install
npm run build
```

Mientras se diseña, `npm run css:watch` regenera el CSS al guardar cada cambio.

## Descripción

Toda la operación está limitada a Cartagena de Indias.

- **Sitio público:** landing (hero con video institucional, servicios, proceso, nosotros, Suite y contacto por WhatsApp), rastreo de guías (sin datos personales), ser aliado (por WhatsApp), privacidad y términos.
- **Suite (`/suite`):** panel para `admin` y `manager`: dashboard, paquetes (crear, filtrar, ver detalle y editar; solo el `admin` elimina), repartidores (crear y editar; solo el `admin` elimina), perfil propio (datos y contraseña) y, solo para `admin`: managers (crear, editar y eliminar) y reportes (solo interfaz).
- **API (`/api`):** autenticación con JWT para la app móvil.

| Rol | Qué hace | Desde dónde ingresa |
|---|---|---|
| `admin` | Administra el sistema (managers y reportes) | Suite |
| `manager` | Crea y edita paquetes y repartidores (no elimina) | Suite |
| `courier` | Reparte los paquetes | App móvil |

Estados de una guía: **Pendiente**, **Recogido**, **Entregado** y **Con novedad**.
El número de guía se asigna automáticamente al crear el paquete: el siguiente disponible, con el formato `DX-000001`.

## Pruebas

Las pruebas usan una base SQLite temporal, así que no tocan los datos de desarrollo:

```bash
pip install -r requirements-dev.txt
pytest
```

Cubren la API (login, estados, motivo de novedad y firma), la Suite (permisos, paquetes, límites de Cartagena y reportes), el sitio público y las migraciones desde cero.

GitHub Actions las corre en cada push y en cada pull request (`.github/workflows/deploy.yml`).

## Producción (Render + Aiven)

La web corre en [Render](https://render.com) (plan Free) y la base de datos es MySQL en [Aiven](https://aiven.io). Cada push a `main` corre las pruebas en GitHub Actions y, si pasan, publica ese commit en Render.

### 1. Base de datos en Aiven

1. Crear un servicio **MySQL** (plan Free).
2. En **Overview > Connection information** se copian `Host`, `Port`, `User` (`avnadmin`), `Password` y `Database name` (`defaultdb`).
3. Descargar el **CA certificate** (`ca.pem`).

### 2. Web service en Render

1. **New > Web Service**, conectar el repositorio y elegir la rama `main`.
2. Configuración:

| Campo | Valor |
|---|---|
| Language | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `flask --app app db:upgrade && flask --app app db:seed && gunicorn --bind 0.0.0.0:$PORT "app:create_app()"` |
| Instance Type | `Free` |

El comando de inicio aplica las migraciones y crea los usuarios iniciales (los que ya existen se omiten) antes de encender el servidor, porque el plan Free no tiene comando previo al deploy ni consola.

3. En **Environment > Environment Variables**:

| Variable | Valor |
|---|---|
| `PYTHON_VERSION` | `3.12.8` |
| `TZ` | `America/Bogota` (las fechas se guardan en hora de Colombia) |
| `SECRET_KEY` | Una clave nueva: `flask --app app key:generate --show` |
| `DB_CONNECTION` | `mysql` |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Los datos de Aiven |
| `DB_SSL_CA` | `/etc/secrets/ca.pem` |
| `WHATSAPP_ADVISOR_NUMBER` | Número del asesor |
| `SEED_*_NAME`, `SEED_*_PASSWORD` | Nombres y contraseñas de los usuarios iniciales (claves fuertes) |

4. En **Environment > Secret Files**, agregar un archivo llamado `ca.pem` con el contenido del certificado de Aiven.
5. En **Settings > Build & Deploy**, poner **Auto-Deploy** en `Off`: el deploy lo hace GitHub Actions después de las pruebas.
6. En **Settings > Deploy Hook**, copiar la dirección.

### 3. Secreto en GitHub

En el repositorio, **Settings > Secrets and variables > Actions > New repository secret**:

| Nombre | Valor |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | La dirección del Deploy Hook de Render |

Desde ese momento, cada push a `main` queda publicado en unos minutos; el avance se ve en la pestaña **Actions** de GitHub y en **Events** de Render.

En el plan Free, la web se apaga tras 15 minutos sin visitas y la primera visita siguiente tarda cerca de un minuto en responder. Los archivos del servidor se borran en cada deploy, por eso la firma de entrega se guarda en la base de datos.

## API

Autenticación con JWT para la app móvil. Las rutas están documentadas en [docs/api.md](docs/api.md).

## Variables de entorno (`.env`)

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Firma la sesión del panel y los tokens JWT. Obligatoria. |
| `DB_CONNECTION` | `sqlite` (por defecto, archivo `instance/dropx.db`) o `mysql` (producción, ej: Aiven). |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Solo con `DB_CONNECTION=mysql`: conexión a MySQL (por defecto `localhost`, `3306`, `root`, sin contraseña y `dropx`). |
| `DB_SSL_CA` | Opcional, solo MySQL. Ruta del certificado `.pem` para servicios en la nube que exigen SSL (en Render: `/etc/secrets/ca.pem`). |
| `JWT_EXPIRES_HOURS` | Duración del token de la API (por defecto, 168 horas = 7 días). |
| `WHATSAPP_ADVISOR_NUMBER` | Número del asesor para el formulario de contacto. |
| `SEED_*_NAME`, `SEED_*_PASSWORD` | Nombres y contraseñas de los usuarios que crea `db:seed` (admin, manager y courier). |

## Arquitectura

- **`app/models.py`:** tablas `users`, `packages` (incluida la firma de entrega, como imagen PNG) y `package_events` (SQLAlchemy).
- **`app/suite.py`, `app/public.py`, `app/api.py`:** rutas del panel, del sitio y de la API (un `Blueprint` por archivo).
- **`app/commands.py`:** comandos `db:seed`, `db:test`, `db:fresh`, `db:upgrade`, `db:migrate` y `key:generate`.
- **Diseño:** [Tailwind CSS](https://tailwindcss.com) v4: las clases van directamente en las plantillas, y los colores y la tipografía de la marca están en `app/static/css/input.css`. Las clases que se repiten (botones, tarjetas, campos) están en `app/templates/_ui.html` y los componentes en `_macros.html`. Iconos SVG, gráficas con Chart.js (copiado a `static/js/vendor/`) y mapas con [Leaflet](https://leafletjs.com) y OpenStreetMap (copiado a `static/vendor/leaflet/`), ambos instalados con npm. Diseño claro, sin modo oscuro. La imagen del hero es una foto local (`static/img/hero-bodega.jpg`), por lo que no depende de internet.
- **Librerías:** Flask-SQLAlchemy y Flask-Migrate (base de datos y migraciones), Flask-Login (sesión del panel), Flask-JWT-Extended (API) y Flask-WTF (protección CSRF de los formularios).

## Estructura de carpetas

```
dropx_web/
├── .github/
│   └── workflows/
│       └── deploy.yml    # GitHub Actions: pruebas en cada push y deploy en Render desde main
├── app/
│   ├── __init__.py       # Crea la app y conecta las extensiones
│   ├── models.py         # Tablas: users, packages y package_events
│   ├── public.py         # Rutas del sitio público (inicio, rastreo, ser aliado)
│   ├── suite.py          # Rutas del panel web (login, paquetes, mapa, reportes, repartidores, managers)
│   ├── api.py            # Rutas de la API (login, paquetes, cambio de estado y firma)
│   ├── commands.py       # Comandos: db:seed, db:test, db:fresh, db:upgrade, db:migrate y key:generate
│   ├── templates/
│   │   ├── public/       # Páginas del sitio (base.html es el diseño común)
│   │   └── suite/        # Páginas del panel (base.html es el diseño común)
│   └── static/
│       ├── css/          # input.css (colores y medidas de Tailwind) y tailwind.css (generado)
│       ├── js/           # site.js (menú y video), suite.js (menú, ventanas), dashboard.js (gráficas), maps.js (mapas) y vendor/chart.umd.js
│       ├── vendor/       # leaflet/ (librería de mapas)
│       └── img/          # Logos, favicon, video y foto del hero
├── docs/
│   ├── api.md            # Rutas de la API
│   └── screenshots/      # Capturas del README
├── instance/             # Datos locales que no se suben a GitHub
│   └── dropx.db          # Base SQLite de desarrollo (se crea sola)
├── migrations/
│   └── versions/         # Migraciones de la base de datos (Flask-Migrate)
├── tests/                # Pruebas con pytest: API, Suite, sitio público y migraciones
├── config.py             # Configuración (lee el .env)
├── package.json          # Comandos de npm (Tailwind, Chart.js y Leaflet)
├── pytest.ini            # Configuración de pytest
├── requirements.txt      # Dependencias de Python (incluye gunicorn para producción)
├── requirements-dev.txt  # Dependencias de Python más pytest (para las pruebas)
├── .env.example          # Modelo del .env (el .env real no se sube a GitHub)
├── .gitignore
└── README.md             # Documentación
```

Al cambiar los modelos, generar una nueva migración y aplicarla:

```bash
flask --app app db:migrate -m "descripcion del cambio"
flask --app app db:upgrade
```

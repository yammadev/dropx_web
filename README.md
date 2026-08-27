# DropX Web

Aplicación web Flask que sienta la base de un panel administrativo y una API para DropX. En el estado actual incluye la configuración de la aplicación, persistencia de usuarios, comandos de preparación de base de datos y dos rutas de comprobación. Aún no implementa la gestión de envíos, paquetes, autenticación ni pantallas de administración.

## Puesta en marcha
### Requerimientos
- **Python 3.9** o superior

### 1. Crear el entorno e instalar dependencias
```bash
# Crear el entorno virtual
py -m venv .venv

# Activar ambiente virtual (Windows)
.venv\Scripts\activate

# Instalar dependencias
py -m pip install -r requirements.txt
```

### 2. Configurar el entorno

Copie la plantilla y genere una clave propia:

```bash
# Configurar variables de entorno
cp .env.example .env
```

Edite `.env` antes de ejecutar la aplicación:

```dotenv
SECRET_KEY=una-clave-larga-aleatoria-y-secreta
DATABASE_URL=sqlite:///dropx.db
```

> `DATABASE_URL` usa SQLite por defecto. Con esa URL, Flask-SQLAlchemy guarda la base local en el directorio `instance/`. No use la clave de ejemplo en entornos compartidos o de producción.

### 3. Preparar la base de datos local

Los comandos siguientes eliminan todas las tablas y datos existentes, luego crean el esquema actual. Deben usarse solamente en desarrollo.

```bash
# Crea el esquema y el usuario administrador inicial
flask --app run:app db-custom refresh

# Actualmente tiene el mismo efecto práctico: recrea el esquema y ejecuta todos los seeders
flask --app run:app db-custom seed
```

> El seeder crea `admin@dropx.com` con la contraseña `admin123`. Cambie o elimine esta cuenta antes de exponer el servicio; no debe usarse fuera de desarrollo.

### 4. Ejecutar

```bash
# Ejecutar
py run.py
```

> El servidor de desarrollo queda disponible en `http://127.0.0.1:5000`. El punto de entrada activa el modo de depuración, por lo que no es apropiado para producción.

### 5. Borrar y empezar de cero (desarrollo)
```bash
# PowerShell
Get-ChildItem -Path . -Directory -Filter __pycache__ -Recurse | Remove-Item -Recurse -Force
Remove-Item -LiteralPath .\instance\dropx.db -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath .\.venv -Recurse -Force -ErrorAction SilentlyContinue
```
## Rutas disponibles

| Método | Ruta | Respuesta actual |
| --- | --- | --- |
| `GET` | `/` | Texto de inicialización del dashboard |
| `GET` | `/api/health` | JSON con el estado `ok` |

Ejemplo de comprobación:

```bash
curl http://127.0.0.1:5000/api/health
```

```json
{"message":"DropX API is running","status":"ok"}
```

## Estructura

```text
dropx_web/
├── app/
│   ├── models/              # Modelos ORM
│   │   ├── __init__.py      # Exportación centralizada de modelos
│   │   └── user.py          # Modelo ORM User y manejo de contraseñas
│   ├── routes/              # Endpoints para la app
│   │   ├── api.py           # Endpoints JSON (/api)
│   │   └── web.py           # Vistas administrativas (/)
│   ├── __init__.py          # Application Factory y carga de .env
│   ├── cli.py               # Comandos personalizados de Flask
│   ├── database.py          # Instancias SQLAlchemy y Flask-Migrate
│   └── seeder.py            # Datos iniciales de desarrollo
├── instance/                # Base de datos SQLite local
├── .env.example             # Plantilla de variables de entorno (.env localmente)
├── .gitignore               # Archivos excluidos del control de versiones
├── requirements.txt         # Dependencias de Python
├── run.py                   # Script ejecutor local
└── README.md                # Documentación del proyecto
```

## Changelog
Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]
#### [0.2.0] - 2026-08-27
**Añadido**
- Modelo ORM `User` con almacenamiento hash de contraseñas.
- Configuración inicial para base de datos, usando *SQLAlchemy*, *Flask-Migrate* y *SQLite* local por defecto.
- Comandos para `seed` y `refresh` base de datos para desarrollo, en custom *CLI*.

#### [0.1.0] - 2026-08-27
**Añadido**
- Estructura base del proyecto Flask utilizando el patrón Application Factory `(app/__init__.py)`.
- Carga de variables de entorno mediante `python-dotenv`.
- Blueprint para la API REST `app/routes/api.py` con endpoint inicial `GET` `/api/health`.
- Blueprint para el Dashboard web `(app/routes/web.py)` con vista raíz `GET` `/`.
- Adopción del estándar de documentación *Google Python Docstrings (PEP 257)* en todo el código fuente.
- Archivo `.env.example` para la configuración compartida entre colaboradores.
- Archivo `.gitignore` para excluir el entorno virtual (`venv`) y credenciales locales (`.env`).
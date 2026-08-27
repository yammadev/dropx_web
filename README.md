# DropX Web (Dashboard & API)

Plataforma administrativa y API REST para la gestión de envíos y paquetes DropX.

---

## Estructura del Repositorio

```text
dropx_web/
├── app/
│   ├── __init__.py          # Application Factory y carga de .env
│   └── routes/              # Módulos de rutas del sistema
│       ├── api.py           # Endpoints JSON (/api)
│       └── web.py           # Vistas administrativas (/)
├── .env                     # Variables locales (no subidas a Git)
├── .env.example             # Plantilla de variables de entorno
├── .gitignore               # Archivos excluidos del control de versiones
├── requirements.txt         # Dependencias de Python
├── run.py                   # Script ejecutor local
└── README.md                # Documentación del proyecto
```

---

## Instrucciones de Inicio
#### Requisitos previos
* **Python 3.9+** instalado. 

### Preparar Entorno
```bash
# Crear el entorno virtual
py -m venv .venv

# Activar ambiente virtual (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

### Ejecutar servidor
```bash
# Ejecutar
py run.py

# Ir a http://127.0.0.1:5000
```

---

## Rutas Disponibles
| Módulo | Endpoint | Método | Descripción |
| :--- | :--- | :---: | :--- |
| **Dashboard Web** | `http://127.0.0.1:5000/` | `GET` | Vista principal del panel administrativo |
| **API REST** | `http://127.0.0.1:5000/api/health` | `GET` | Estado operacional del servicio API |

## Changelog
Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]

#### [0.1.0] - 2026-08-27
**Agregado**
- Estructura base del proyecto Flask utilizando el patrón Application Factory `(app/__init__.py)`.
- Carga de variables de entorno mediante `python-dotenv`.
- Blueprint para la API REST `app/routes/api.py` con endpoint inicial `GET` `/api/health`.
- Blueprint para el Dashboard web `(app/routes/web.py)` con vista raíz `GET` `/`.
- Adopción del estándar de documentación *Google Python Docstrings (PEP 257)* en todo el código fuente.
- Archivo `.env.example` para la configuración compartida entre colaboradores.
- Archivo `.gitignore` para excluir el entorno virtual (`venv`) y credenciales locales (`.env`).
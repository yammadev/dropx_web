import os
import sqlite3
from datetime import datetime
from flask import Flask, url_for
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

# ---------- Extensiones ----------
# Se crean aquí vacías y se conectan a la app dentro de create_app()
db = SQLAlchemy()  # base de datos (modelos y consultas)
migrate = Migrate()  # migraciones (cambios en la estructura de las tablas)
login_manager = LoginManager()  # sesión del panel web
jwt = JWTManager()  # tokens de la API
csrf = CSRFProtect()  # protección de los formularios del panel

# Si alguien entra al panel sin sesión, se le envía al login
login_manager.login_view = 'suite.login'
login_manager.login_message = 'Inicie sesión para acceder a la Suite logística.'
login_manager.login_message_category = 'danger'


@event.listens_for(Engine, 'connect')
def enable_sqlite_foreign_keys(connection, record):
    """SQLite no revisa las llaves foráneas si no se le pide (MySQL sí lo hace siempre)."""
    if isinstance(connection, sqlite3.Connection):
        connection.execute('PRAGMA foreign_keys=ON')


def create_app():
    """Crea y configura la aplicación (patrón "application factory" de Flask)."""
    app = Flask(__name__)
    app.config.from_object(Config)
    # En producción (Render) la app queda detrás de un proxy que recibe el HTTPS: así Flask sabe
    # que la visita llegó por HTTPS y con qué dirección IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    os.makedirs(app.instance_path, exist_ok=True)  # aquí vive el archivo SQLite de desarrollo

    # Si falta la SECRET_KEY el sitio avisa cómo crearla. No se lanza un error al
    # arrancar para que el comando "flask --app app key:generate" pueda ejecutarse.
    @app.before_request
    def check_secret_key():
        if not app.config['SECRET_KEY']:
            return 'Falta SECRET_KEY en el .env. Ejecute: flask --app app key:generate', 500

    # Conectar las extensiones a la app
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)  # SQLite no puede alterar columnas sin esto
    login_manager.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    # Importar los modelos para que las migraciones los detecten
    from app import models

    # Rutas: sitio público, panel web (/suite) y API (/api)
    from app import api, public, suite
    app.register_blueprint(public.bp)
    app.register_blueprint(suite.bp)
    app.register_blueprint(api.bp)
    csrf.exempt(api.bp)  # la API usa tokens JWT, no cookies, así que no necesita CSRF

    # Revisión de salud: Render la consulta (Health Check Path = /health) para saber
    # que el servidor encendió antes de dejarlo recibir visitas
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # Filtros de plantilla (se usan así: {{ nombre|tone }})
    @app.template_filter('initials')
    def initials(name):
        """Iniciales de las dos primeras palabras: 'Carlos Pérez' -> 'CP'."""
        return ''.join(word[0] for word in (name or '?').split()[:2]).upper()

    @app.template_filter('tone')
    def tone(name):
        """Número de 0 a 3 que elige el color del avatar según el nombre."""
        return (ord(name[0]) + len(name)) % 4 if name else 0

    @app.template_filter('place')
    def place(address):
        """Barrio de una dirección: 'Cl 3 # 4-5 - B/ Manga' -> 'Manga'."""
        text = address.split(' - ')[-1] if ' - ' in address else address.split(',')[0]
        return text.removeprefix('B/ ').strip()

    @app.template_filter('short_date')
    def short_date(date):
        """Fecha corta en español: '05 Nov'."""
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return f'{date.day:02d} {months[date.month - 1]}' if date else '—'

    # Comandos de consola: db:seed, db:fresh, db:upgrade, db:migrate y key:generate
    from app import commands
    app.cli.add_command(commands.seed_command)
    app.cli.add_command(commands.test_command)
    app.cli.add_command(commands.fresh_command)
    app.cli.add_command(commands.upgrade_command)
    app.cli.add_command(commands.migrate_command)
    app.cli.add_command(commands.key_command)

    # Se recarga una plantilla modificada sin reiniciar el servidor
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Enlace a un archivo CSS/JS con la fecha de modificación (?v=...), para que el navegador
    # descargue de nuevo el archivo cuando cambia en lugar de usar una copia guardada (caché).
    def asset(filename):
        path = os.path.join(app.static_folder, filename)
        version = int(os.path.getmtime(path)) if os.path.exists(path) else 0
        return url_for('static', filename=filename, v=version)

    # Variables y funciones disponibles en todas las plantillas
    @app.context_processor
    def inject_globals():
        return {'STATUSES': models.STATUSES, 'now_year': datetime.now().year, 'asset': asset}

    return app

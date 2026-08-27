"""Módulo de la fábrica de la aplicación (Application Factory)."""

import os
from flask import Flask
from dotenv import load_dotenv
from app.database import db, migrate
from app.cli import register_cli_commands

# Carga variables de entorno desde el archivo .env
load_dotenv()


def create_app() -> Flask:
    """Crea y configura una instancia de la aplicación Flask.

    Returns:
        Flask: Instancia de la aplicación Flask totalmente configurada.
    """
    flask_app = Flask(__name__)

    # Configuración de variables de entorno con fallback para desarrollo
    flask_app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret-key-dev")
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///dropx.db"
    )
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializar DB y Migrate
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    # Registrar comandos CLI personalizados
    register_cli_commands(flask_app)

    # Importar el paquete de modelos para Alembic
    import app.models  # noqa: F401

    # Blueprints
    from app.routes.api import api_bp
    from app.routes.web import web_bp

    flask_app.register_blueprint(web_bp)
    flask_app.register_blueprint(api_bp, url_prefix="/api")

    return flask_app
"""Módulo de la fábrica de la aplicación (Application Factory).

Inicializa la app de Flask, carga la configuración de variables de entorno
y registra los Blueprints de las rutas.
"""

import os
from flask import Flask
from dotenv import load_dotenv

# Carga variables de entorno desde el archivo .env
load_dotenv()


def create_app() -> Flask:
    """Crea y configura una instancia de la aplicación Flask.

    Returns:
        Flask: Instancia de la aplicación Flask totalmente configurada.
    """
    app = Flask(__name__)

    # Configuración de variables de entorno con fallback para desarrollo
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback-secret-key-dev")

    # Importación y registro de Blueprints
    from app.routes.api import api_bp
    from app.routes.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
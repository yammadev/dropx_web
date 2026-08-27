"""Módulo de configuración de la base de datos.

Mantiene las instancias de SQLAlchemy y Flask-Migrate aisladas.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
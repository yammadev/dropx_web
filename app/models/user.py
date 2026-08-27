"""Módulo del modelo de usuario.

Define la entidad User para administradores y usuarios de DropX.
"""

from zoneinfo import ZoneInfo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import db


class User(db.Model):
    """Modelo ORM que representa un usuario del sistema."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(120), unique = True, nullable = False)
    password_hash = db.Column(db.String(256), nullable = False)
    full_name = db.Column(db.String(100), nullable = False)
    role = db.Column(db.String(20), default = "admin")  # admin, driver, client
    created_at = db.Column(db.DateTime, default = datetime.now(ZoneInfo("America/Bogota"))) # Hora y fecha en zona horaria de Colombia

    def set_password(self, password: str) -> None:
        """Genera el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica la contraseña ingresada contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)
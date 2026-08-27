"""Módulo para poblar datos iniciales (Seeder).

Inserta el usuario administrador por defecto si no existe en la base de datos.
"""

from app.database import db
from app.models import User


def seed_default_admin() -> None:
    """Crea un usuario admin por defecto de forma automática."""
    default_email = "admin@dropx.com"

    admin_exists = User.query.filter_by(email = default_email).first()

    if not admin_exists:
        admin = User(
            email = default_email, full_name = "Admin", role = "admin"
        )
        admin.set_password("admin123")

        db.session.add(admin)
        db.session.commit()
        print(f"[Seeder] Usuario Admin creado por defecto: {default_email}")
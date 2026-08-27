"""Módulo de comandos de línea de comandos (CLI) personalizados para Flask.

Permite resetear la base de datos y poblar datos iniciales o de pruebas.
"""

import click
from flask.cli import AppGroup
from app.database import db
from app.seeder import seed_default_admin

db_cli = AppGroup("db-custom", help = "Comandos de gestión y seeding de la base de datos.")


@db_cli.command("seed")
def seed_all():
    """Borra la base de datos, recrea las tablas y ejecuta los seeders completos."""
    click.echo("Reiniciando base de datos...")
    db.drop_all()
    db.create_all()

    click.echo("Ejecutando seeders...")
    seed_default_admin()

    # Futuro: Generación de datos de prueba con Faker (Drivers, Packages, etc.)
    click.echo("¡Base de datos reseteada y poblada exitosamente!")


@db_cli.command("refresh")
def refresh_admin_only():
    """Borra la base de datos, recrea las tablas y genera ÚNICAMENTE el usuario Admin."""
    click.echo("Limpiando base de datos...")
    db.drop_all()
    db.create_all()

    seed_default_admin()
    click.echo("¡Base de datos reseteada únicamente con el usuario Admin!")


def register_cli_commands(app):
    """Registra los comandos de CLI en la instancia de Flask.

    Args:
        app: Instancia de la aplicación Flask.
    """
    app.cli.add_command(db_cli)
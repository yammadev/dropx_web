import os
import random
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import click
from flask.cli import with_appcontext
from flask_migrate import migrate, upgrade

from app import db
from app.models import Package, PackageEvent, User

# Carpeta principal del proyecto (donde vive el archivo .env)
ROOT = Path(__file__).resolve().parent.parent

# Usuarios iniciales: (prefijo de las variables del .env, nombre por defecto, correo, rol)
# El nombre sale de <PREFIJO>_NAME y la contraseña de <PREFIJO>_PASSWORD
USERS = [
    ('SEED_ADMIN', 'Administrador', 'admin@dropx.com', 'admin'),
    ('SEED_MANAGER', 'Manager', 'manager@dropx.com', 'manager'),
    ('SEED_COURIER', 'Jhon Doe', 'courier@dropx.com', 'courier'),
]


# Repartidores de prueba: (nombre, correo, teléfono). Usan la contraseña SEED_COURIER_PASSWORD.
TEST_COURIERS = [
    ('Carlos Pérez', 'carlos@dropx.com', '300 123 4567'),
    ('Ana Ruiz', 'ana@dropx.com', '301 234 5678'),
    ('Luis Gómez', 'luis@dropx.com', '302 345 6789'),
    ('María Torres', 'maria@dropx.com', '310 456 7890'),
]

# Barrios de Cartagena para las direcciones de prueba, con su ubicación aproximada (latitud, longitud)
TEST_PLACES = {
    'B/ Bocagrande': (10.4020, -75.5560), 'B/ Getsemaní': (10.4229, -75.5460), 'B/ Manga': (10.4105, -75.5340),
    'B/ El Laguito': (10.3900, -75.5640), 'B/ Crespo': (10.4450, -75.5190), 'B/ Castillogrande': (10.3960, -75.5590),
    'B/ Torices': (10.4290, -75.5190), 'B/ Pie de la Popa': (10.4220, -75.5280), 'B/ El Cabrero': (10.4330, -75.5430),
    'B/ Los Alpes': (10.3890, -75.4830),
}
TEST_PEOPLE = ['Laura Gómez', 'Harry Cruz', 'Sofía Mendoza', 'Juan Cruz', 'Carolina Díaz', 'Pedro Salas', 'Marta Rojas']


def create_users():
    """Crea los usuarios iniciales. Los que ya existen se omiten."""
    for prefix, default_name, email, role in USERS:
        if User.query.filter_by(email=email).first():
            click.echo(f'Ya existe: {email}')
            continue

        password = os.getenv(f'{prefix}_PASSWORD')
        if not password:
            raise click.ClickException(f'Falta {prefix}_PASSWORD en el archivo .env')

        user = User(name=os.getenv(f'{prefix}_NAME') or default_name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        click.echo(f'Creado: {email} ({role})')

    db.session.commit()


def reset_database():
    """Borra TODAS las tablas y las crea de nuevo con las migraciones."""
    db.reflect()  # lee las tablas que existen en la base (incluida alembic_version)
    db.drop_all()  # las borra todas
    click.echo('Tablas eliminadas.')
    upgrade()  # vuelve a crearlas


# ---------- flask --app app db:seed ----------
@click.command('db:seed')
@with_appcontext
def seed_command():
    """Crea los usuarios iniciales (admin, manager y courier)."""
    create_users()


# ---------- flask --app app db:test ----------
@click.command('db:test')
@click.option('--packages', default=40, show_default=True, help='Cantidad de paquetes de prueba.')
@click.option('--yes', is_flag=True, help='No pedir confirmación.')
@with_appcontext
def test_command(packages, yes):
    """Reinicia la base de datos y crea usuarios, repartidores y paquetes de prueba (solo para desarrollo)."""
    password = os.getenv('SEED_COURIER_PASSWORD')
    if not password:
        raise click.ClickException('Falta SEED_COURIER_PASSWORD en el archivo .env')

    if not yes:
        click.confirm('Se borrarán todas las tablas y todos los datos. ¿Continuar?', abort=True)

    # Base de datos nueva y usuarios iniciales
    reset_database()
    create_users()

    # Repartidores de prueba
    for name, email, phone in TEST_COURIERS:
        user = User(name=name, email=email, role='courier', phone=phone)
        user.set_password(password)
        db.session.add(user)
        click.echo(f'Creado: {email} (courier)')
    db.session.commit()

    couriers = User.query.filter_by(role='courier').all()
    rng = random.Random(7)  # misma semilla: siempre salen los mismos datos
    now = datetime.now()
    for number in range(1, packages + 1):
        status = rng.choices(['pending', 'picked_up', 'delivered', 'issue'], [3, 3, 6, 1])[0]
        created = now - timedelta(days=rng.randint(0, 150), hours=rng.randint(0, 8))
        # Los pendientes más recientes, para que se vean en la app
        if status == 'pending':
            created = now - timedelta(days=rng.randint(0, 3))
        # La mitad de las entregas son de este mes, para que se vean en el dashboard
        if status == 'delivered' and rng.random() < 0.5:
            created = now - timedelta(days=rng.randint(0, max(now.day - 1, 1)), hours=rng.randint(3, 8))
        origin, destination = rng.choice(list(TEST_PLACES)), rng.choice(list(TEST_PLACES))
        package = Package(
            tracking_number=f'DX-{number:06d}',
            weight=rng.choice([1.2, 2.5, 3.8, 5.5, 7, 9.5, 12, 15.5, 22.5]),
            distance_km=round(rng.uniform(1.5, 12), 1),
            is_urgent=rng.random() < 0.2,
            status=status,
            sender_name=rng.choice(TEST_PEOPLE),
            sender_document='CC 1.100.000.000',
            sender_phone='300 500 00 00',
            origin_address=f'Cl {rng.randint(1, 70)} # {rng.randint(1, 60)}-{rng.randint(1, 99)} - {origin}',
            origin_lat=TEST_PLACES[origin][0] + rng.uniform(-0.004, 0.004),
            origin_lng=TEST_PLACES[origin][1] + rng.uniform(-0.004, 0.004),
            recipient_name=rng.choice(TEST_PEOPLE),
            recipient_document='CC 1.045.000.000',
            recipient_phone='311 200 00 00',
            destination_address=f'Cr {rng.randint(1, 70)} # {rng.randint(1, 60)}-{rng.randint(1, 99)} - {destination}',
            destination_lat=TEST_PLACES[destination][0] + rng.uniform(-0.004, 0.004),
            destination_lng=TEST_PLACES[destination][1] + rng.uniform(-0.004, 0.004),
            issue_reason='Destinatario ausente' if status == 'issue' else None,
            courier_id=rng.choice(couriers).id,
            created_at=created,
            delivered_at=min(created + timedelta(hours=rng.randint(2, 30)), now) if status == 'delivered' else None,
        )
        # Historial: del más antiguo al más reciente (la relación los muestra al revés)
        steps = [('Guía generada', 'Registrada en la Suite.', created)]
        if status != 'pending':
            steps.append(('Recogido', 'El repartidor recogió el paquete.', created + timedelta(hours=1)))
        if status == 'delivered':
            steps.append(('Entregado', 'Paquete entregado al destinatario.', package.delivered_at))
        if status == 'issue':
            steps.append(('Con novedad', 'Destinatario ausente.', created + timedelta(hours=3)))
        for title, description, when in steps:
            package.events.append(PackageEvent(title=title, description=description, created_at=when))
        db.session.add(package)
    db.session.commit()
    click.echo(f'Creados {packages} paquetes de prueba.')


# ---------- flask --app app db:fresh ----------
@click.command('db:fresh')
@click.option('--yes', is_flag=True, help='No pedir confirmación.')
@click.option('--no-seed', is_flag=True, help='No crear los usuarios iniciales.')
@with_appcontext
def fresh_command(yes, no_seed):
    """Borra TODAS las tablas, las crea de nuevo y siembra los usuarios (solo para desarrollo)."""
    if not yes:
        click.confirm('Se borrarán todas las tablas y todos los datos. ¿Continuar?', abort=True)

    reset_database()
    if not no_seed:
        create_users()


# ---------- flask --app app db:upgrade ----------
@click.command('db:upgrade')
@with_appcontext
def upgrade_command():
    """Crea o actualiza las tablas aplicando las migraciones pendientes."""
    upgrade()


# ---------- flask --app app db:migrate -m "descripción" ----------
@click.command('db:migrate')
@click.option('-m', '--message', required=True, help='Descripción del cambio en los modelos.')
@with_appcontext
def migrate_command(message):
    """Genera una migración nueva a partir de los cambios en app/models.py."""
    migrate(message=message)


# ---------- flask --app app key:generate ----------
@click.command('key:generate')
@click.option('--show', is_flag=True, help='Solo mostrar la clave, sin guardarla.')
def key_command(show):
    """Genera una SECRET_KEY nueva y la guarda en el archivo .env."""
    key = secrets.token_hex(32)
    if show:
        click.echo(key)
        return

    env_file = ROOT / '.env'
    example = ROOT / '.env.example'
    # Si todavía no existe el .env, se parte de una copia del .env.example
    if env_file.exists():
        text = env_file.read_text(encoding='utf-8')
    elif example.exists():
        text = example.read_text(encoding='utf-8')
    else:
        text = ''

    # Reemplazar la línea SECRET_KEY (o agregarla si no existe)
    line = f'SECRET_KEY={key}'
    if re.search(r'^SECRET_KEY=.*$', text, flags=re.M):
        text = re.sub(r'^SECRET_KEY=.*$', lambda _: line, text, flags=re.M)
    else:
        text = text.rstrip('\n') + f'\n{line}\n'

    env_file.write_text(text, encoding='utf-8')
    click.echo('SECRET_KEY generada y guardada en .env')
    click.echo('Aviso: al cambiarla se cierran las sesiones y los tokens existentes.')

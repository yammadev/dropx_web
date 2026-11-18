"""Piezas compartidas por todas las pruebas (pytest las encuentra solo)."""
import pytest

from app import create_app, db
from app.models import Package, User
from config import Config

# Contraseña de todos los usuarios de prueba
PASSWORD = 'clave-12345'


@pytest.fixture
def app(tmp_path, monkeypatch):
    """App con una base SQLite temporal: cada prueba empieza desde cero y no toca los datos reales."""
    # tmp_path es una carpeta temporal que pytest borra al terminar
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path / "test.db"}')
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-de-pruebas-clave-de-pruebas-123')
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)  # sin CSRF para poder enviar formularios

    with app.app_context():
        db.create_all()

        # Un usuario de cada rol, más un segundo repartidor para probar permisos
        for name, email, role, phone in [
            ('Admin', 'admin@test.com', 'admin', None),
            ('Manager', 'manager@test.com', 'manager', None),
            ('Courier Uno', 'courier@test.com', 'courier', '3001111111'),
            ('Courier Dos', 'otro@test.com', 'courier', '3002222222'),
        ]:
            user = User(name=name, email=email, role=role, phone=phone)
            user.set_password(PASSWORD)
            db.session.add(user)
        db.session.commit()

        # Un paquete pendiente, asignado a "Courier Uno"
        courier = User.query.filter_by(email='courier@test.com').first()
        db.session.add(Package(
            tracking_number='DX-000001', weight=2, status='pending', courier_id=courier.id,
            sender_name='Remitente', sender_phone='3000000000', origin_address='Bocagrande',
            recipient_name='Destinatario', recipient_phone='3000000001', destination_address='Manga',
        ))
        db.session.commit()
    return app


@pytest.fixture
def client(app):
    """Navegador de mentira: hace peticiones a la app sin encender el servidor."""
    return app.test_client()


def api_headers(client, email):
    """Inicia sesión en la API y devuelve el encabezado con el token (como lo hace la app móvil)."""
    token = client.post('/api/auth/login', json={'email': email, 'password': PASSWORD}).json['token']
    return {'Authorization': f'Bearer {token}'}


def suite_login(client, email):
    """Inicia sesión en la Suite (el cliente guarda la cookie de sesión)."""
    return client.post('/suite/login', data={'email': email, 'password': PASSWORD})

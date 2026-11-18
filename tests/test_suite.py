"""Pruebas del panel web (/suite): permisos, paquetes, mapa y reportes."""
from app.models import Package
from tests.conftest import PASSWORD, suite_login

# Datos mínimos del formulario de un paquete nuevo
PAQUETE = {
    'sender_name': 'Ana', 'sender_phone': '3001234567', 'origin_address': 'Bocagrande',
    'recipient_name': 'Luis', 'recipient_phone': '3007654321', 'destination_address': 'Manga',
    'weight': '2.5', 'distance_km': '4',
}
# Ubicaciones dentro de Cartagena y una fuera (Bogotá)
CARTAGENA = {'origin_lat': '10.40', 'origin_lng': '-75.55', 'destination_lat': '10.42', 'destination_lng': '-75.50'}
BOGOTA = {'origin_lat': '4.65', 'origin_lng': '-74.08'}


# ---------- Acceso ----------
def test_la_suite_exige_sesion(client):
    # Sin sesión, redirige al login
    response = client.get('/suite/dashboard')
    assert response.status_code == 302
    assert '/suite/login' in response.headers['Location']


def test_el_repartidor_no_entra_a_la_suite(client):
    response = suite_login(client, 'courier@test.com')
    assert response.status_code == 200  # se queda en el login con un aviso
    assert client.get('/suite/dashboard').status_code == 302  # y no tiene sesión


def test_admin_y_manager_entran(client):
    for email in ('admin@test.com', 'manager@test.com'):
        assert suite_login(client, email).status_code == 302  # login correcto: redirige al dashboard
        assert client.get('/suite/dashboard').status_code == 200
        client.get('/suite/logout')


def test_paginas_principales_cargan(client):
    suite_login(client, 'admin@test.com')
    for url in ('/suite/paquetes', '/suite/paquetes/nuevo', '/suite/paquetes/1', '/suite/mapa',
                '/suite/repartidores', '/suite/managers', '/suite/reportes'):
        assert client.get(url).status_code == 200, url  # el mensaje dice cuál página falló


# ---------- Crear paquetes ----------
def test_crear_paquete_con_ubicaciones_en_cartagena(client, app):
    suite_login(client, 'manager@test.com')
    response = client.post('/suite/paquetes/nuevo', data=PAQUETE | CARTAGENA)
    assert response.status_code == 302  # creado: redirige al detalle
    with app.app_context():
        # El número de guía es el siguiente al que ya existía (DX-000001)
        package = Package.query.filter_by(tracking_number='DX-000002').first()
        assert package.origin_lat == 10.40
        assert package.events[0].title == 'Guía generada'


def test_no_acepta_ubicaciones_fuera_de_cartagena(client, app):
    suite_login(client, 'manager@test.com')
    response = client.post('/suite/paquetes/nuevo', data=PAQUETE | BOGOTA)
    assert response.status_code == 200  # vuelve al formulario con el aviso
    assert 'dentro de Cartagena' in response.get_data(as_text=True)
    with app.app_context():
        assert Package.query.count() == 1  # no se creó nada


def test_el_peso_debe_ser_valido(client):
    suite_login(client, 'manager@test.com')
    response = client.post('/suite/paquetes/nuevo', data=PAQUETE | {'weight': '0'})
    assert 'peso mayor que cero' in response.get_data(as_text=True)


# ---------- Cosas solo del administrador ----------
def test_reportes_solo_para_admin(client):
    suite_login(client, 'manager@test.com')
    assert client.get('/suite/reportes').status_code == 302


def test_reporte_en_csv(client):
    suite_login(client, 'admin@test.com')
    response = client.get('/suite/reportes?tipo=paquetes&desde=2000-01-01&descargar=1')
    assert response.mimetype == 'text/csv'
    assert response.data.startswith('﻿'.encode('utf-8'))  # BOM para que Excel respete las tildes
    assert b'DX-000001' in response.data


def test_solo_admin_elimina_paquetes(client, app):
    # El manager lo intenta: no se borra nada
    suite_login(client, 'manager@test.com')
    assert client.post('/suite/paquetes/1/eliminar').status_code == 302
    with app.app_context():
        assert Package.query.count() == 1
    client.get('/suite/logout')

    # El admin sí puede
    suite_login(client, 'admin@test.com')
    client.post('/suite/paquetes/1/eliminar')
    with app.app_context():
        assert Package.query.count() == 0


# ---------- Cambio de contraseña sin sesión (lo abre la app desde el perfil) ----------
def test_cambiar_contrasena_sin_sesion(client):
    datos = {'email': 'courier@test.com', 'current_password': PASSWORD,
             'new_password': 'nueva-clave-1', 'confirm_password': 'nueva-clave-1'}
    assert client.get('/suite/cambiar-contrasena').status_code == 200
    assert client.post('/suite/cambiar-contrasena', data=datos).status_code == 302  # cambio correcto
    # La API (app móvil) ya acepta la nueva y rechaza la anterior
    nueva = client.post('/api/auth/login', json={'email': 'courier@test.com', 'password': 'nueva-clave-1'})
    vieja = client.post('/api/auth/login', json={'email': 'courier@test.com', 'password': PASSWORD})
    assert nueva.status_code == 200 and vieja.status_code == 401


def test_cambiar_contrasena_valida_los_datos(client):
    base = {'email': 'courier@test.com', 'current_password': PASSWORD,
            'new_password': 'nueva-clave-1', 'confirm_password': 'nueva-clave-1'}
    # Contraseña actual incorrecta, nueva muy corta y confirmación distinta: no cambia nada
    for cambio in ({'current_password': 'otra-cosa'}, {'new_password': 'corta', 'confirm_password': 'corta'},
                   {'confirm_password': 'diferente-1'}):
        assert client.post('/suite/cambiar-contrasena', data=base | cambio).status_code == 200
    assert client.post('/api/auth/login', json={'email': 'courier@test.com', 'password': PASSWORD}).status_code == 200


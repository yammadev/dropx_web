"""Pruebas del sitio público (no necesitan sesión)."""


def test_paginas_publicas_cargan(client):
    for url in ('/', '/rastreo', '/ser-aliado', '/privacidad', '/terminos'):
        assert client.get(url).status_code == 200, url  # el mensaje dice cuál página falló


def test_rastreo_de_una_guia_existente(client):
    # La guía se escribe en minúscula a propósito: el rastreo la pasa a mayúscula
    html = client.get('/rastreo?guia=dx-000001').get_data(as_text=True)
    assert 'DX-000001' in html
    assert 'Pendiente' in html


def test_rastreo_de_una_guia_que_no_existe(client):
    response = client.get('/rastreo?guia=DX-999999')
    assert response.status_code == 200  # la página muestra el aviso de "no encontrada"
    assert 'DX-000001' not in response.get_data(as_text=True)


def test_revision_de_salud(client):
    # Render consulta /health en cada deploy: debe responder 200
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}

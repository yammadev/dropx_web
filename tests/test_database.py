"""Pruebas de la base de datos: migraciones y comandos."""
from app import db
from app.models import User


def test_db_fresh_aplica_las_migraciones_y_crea_los_usuarios(app, monkeypatch):
    """Las migraciones corren desde cero y db:fresh crea los usuarios."""
    # Nombres y contraseñas que db:fresh lee del .env
    for role in ('ADMIN', 'MANAGER', 'COURIER'):
        monkeypatch.setenv(f'SEED_{role}_NAME', role.title())
        monkeypatch.setenv(f'SEED_{role}_PASSWORD', 'clave-12345')

    result = app.test_cli_runner().invoke(args=['db:fresh', '--yes'])

    assert result.exit_code == 0, result.output
    with app.app_context():
        assert sorted(user.role for user in User.query.all()) == ['admin', 'courier', 'manager']
        # La última migración (firma en la base de datos) quedó aplicada
        assert 'signature' in [column['name'] for column in db.inspect(db.engine).get_columns('packages')]

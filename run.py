"""Punto de entrada principal de la aplicación.

Ejecuta el servidor de desarrollo de Flask importando la función factory.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
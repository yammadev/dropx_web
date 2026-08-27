"""Módulo de rutas para el Dashboard web.

Maneja las vistas principales del panel administrativo.
"""

from flask import Blueprint

web_bp = Blueprint("web", __name__)

# [GET] /
@web_bp.route("/")
def index():
    """Muestra la vista principal del Dashboard.

    Returns:
        tuple: Mensaje en texto plano de confirmación y código HTTP 200.
    """
    return "DropX Admin Dashboard API - Initialized", 200
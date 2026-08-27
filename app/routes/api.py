"""Módulo de rutas para la API REST.

Maneja los endpoints JSON para clientes externos como la app móvil.
"""

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)

# [GET] /health
@api_bp.route("/health", methods = ["GET"])
def health_check():
    """Comprueba el estado del servicio de la API.

    Returns:
        tuple: Objeto JSON con el estado operacional y código de respuesta HTTP 200.
    """
    return jsonify({"status": "ok", "message": "DropX API is running"}), 200
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager

# ---------- Constantes ----------
# Roles del sistema
ROLES = ('admin', 'manager', 'courier')

# Estados de una guía (clave guardada en la base de datos -> texto que se muestra).
# Son los mismos estados de la app: Pendiente, Recogido, Entregado y Con novedad.
STATUSES = {
    'pending': 'Pendiente',
    'picked_up': 'Recogido',
    'delivered': 'Entregado',
    'issue': 'Con novedad',
}


# ---------- Usuarios ----------
class User(UserMixin, db.Model):
    """Cualquier persona que inicia sesión: admin, manager o courier."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager o courier
    phone = db.Column(db.String(30))  # se usa en los couriers
    created_at = db.Column(db.DateTime, default=datetime.now, server_default=db.text('CURRENT_TIMESTAMP'))

    # La contraseña nunca se guarda en texto plano
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Datos que devuelve la API (sin la contraseña)
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}


# ---------- Paquetes (guías) ----------
class Package(db.Model):
    """Una guía de envío. Los campos coinciden con el modelo de la app (PackageModel)."""

    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(20), unique=True, nullable=False)  # ej: DX-000001
    weight = db.Column(db.Float, nullable=False)  # en kilogramos
    distance_km = db.Column(db.Float, nullable=False, default=0)
    is_urgent = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text('0'))
    status = db.Column(db.String(20), nullable=False, default='pending')

    # Quien envía
    sender_name = db.Column(db.String(120), nullable=False)
    sender_document = db.Column(db.String(30))  # ej: CC 1.100.000.000
    sender_phone = db.Column(db.String(30), nullable=False)
    origin_address = db.Column(db.String(255), nullable=False)
    origin_lat = db.Column(db.Float)  # ubicación en el mapa (opcional)
    origin_lng = db.Column(db.Float)

    # Quien recibe
    recipient_name = db.Column(db.String(120), nullable=False)
    recipient_document = db.Column(db.String(30))
    recipient_phone = db.Column(db.String(30), nullable=False)
    destination_address = db.Column(db.String(255), nullable=False)
    destination_lat = db.Column(db.Float)
    destination_lng = db.Column(db.Float)

    # Motivo de la novedad (solo mientras el estado es "issue")
    issue_reason = db.Column(db.String(100))

    # Repartidor asignado (vacío mientras no se asigne)
    courier_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))

    created_at = db.Column(db.DateTime, default=datetime.now, server_default=db.text('CURRENT_TIMESTAMP'))
    updated_at = db.Column(
        db.DateTime, default=datetime.now, server_default=db.text('CURRENT_TIMESTAMP'), onupdate=datetime.now
    )
    delivered_at = db.Column(db.DateTime)  # se llena cuando el estado pasa a "delivered"

    # Firma de quien recibe: imagen PNG guardada en la base de datos (en MySQL, MEDIUMBLOB de hasta 16 MB).
    # "deferred" hace que solo se lea cuando se usa, para que las listas de paquetes no la carguen.
    signature = db.deferred(db.Column(db.LargeBinary().with_variant(MEDIUMBLOB(), 'mysql')))

    courier = db.relationship('User')
    events = db.relationship(
        'PackageEvent',
        order_by='PackageEvent.id.desc()',  # el más reciente primero
        cascade='all, delete-orphan',  # al borrar el paquete se borra su historial
    )

    @property
    def status_label(self):
        return STATUSES[self.status]

    # Datos que devuelve la API (mismos nombres que usa el modelo de la app)
    def to_dict(self):
        return {
            'id': self.id,
            'number': self.tracking_number,
            'weightKg': self.weight,
            'distanceKm': self.distance_km,
            'isUrgent': self.is_urgent,
            'status': self.status,
            'originAddress': self.origin_address,
            'destinationAddress': self.destination_address,
            'originLat': self.origin_lat,
            'originLng': self.origin_lng,
            'destinationLat': self.destination_lat,
            'destinationLng': self.destination_lng,
            'issueReason': self.issue_reason,
            'sender': {
                'name': self.sender_name,
                'document': self.sender_document,
                'phone': self.sender_phone,
            },
            'receiver': {
                'name': self.recipient_name,
                'document': self.recipient_document,
                'phone': self.recipient_phone,
            },
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }


class PackageEvent(db.Model):
    """Historial de movimientos de una guía (lo que se ve en el rastreo)."""

    __tablename__ = 'package_events'

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(
        db.Integer, db.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, server_default=db.text('CURRENT_TIMESTAMP'))


# Flask-Login usa esta función para saber quién tiene la sesión abierta
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

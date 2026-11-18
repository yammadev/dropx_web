import csv
import io
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import STATUSES, Package, PackageEvent, User

# Panel web (Suite logística): todas las rutas de este archivo empiezan con /suite
bp = Blueprint('suite', __name__, url_prefix='/suite')

# Roles que pueden entrar al panel (el courier solo usa la app)
WEB_ROLES = ('admin', 'manager')

# Meta mensual de entregas por repartidor
MONTHLY_GOAL = 50

# Zona de Cartagena donde se pueden marcar ubicaciones: ((lat. sur, long. oeste), (lat. norte, long. este))
CARTAGENA_BOUNDS = ((10.25, -75.70), (10.55, -75.40))

MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# Campos de texto del formulario de paquetes
PACKAGE_TEXT_FIELDS = (
    'sender_name', 'sender_document', 'sender_phone', 'origin_address',
    'recipient_name', 'recipient_document', 'recipient_phone', 'destination_address',
)
# Campos de texto obligatorios (el documento es opcional)
PACKAGE_REQUIRED_FIELDS = (
    'sender_name', 'sender_phone', 'origin_address',
    'recipient_name', 'recipient_phone', 'destination_address',
)


# Los mapas de las plantillas usan los mismos límites
# Datos de un paquete para dibujarlo en los mapas (origen, destino y estado)
def map_point(p):
    return {
        'number': p.tracking_number,
        'status': p.status,
        'label': p.status_label,
        'from': [p.origin_lat, p.origin_lng],
        'to': [p.destination_lat, p.destination_lng],
        'origin': p.origin_address,
        'destination': p.destination_address,
        'url': url_for('suite.paquete', package_id=p.id),
    }


@bp.context_processor
def map_bounds():
    return {'cartagena_bounds': CARTAGENA_BOUNDS}


# ---------- Ayudas ----------
def admin_required(view):
    """Permite la ruta solo al administrador."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acceso denegado: esta sección es exclusiva del administrador.', 'danger')
            return redirect(url_for('suite.dashboard'))
        return view(*args, **kwargs)

    return login_required(wrapper)


def month_start(date):
    """Primer instante del mes de la fecha dada."""
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def status_counts():
    """Cantidad de paquetes por estado: {'pending': 3, 'delivered': 5, ...}"""
    return dict(db.session.query(Package.status, func.count()).group_by(Package.status))


def add_event(package, title, description=None):
    """Agrega un movimiento al historial del paquete."""
    package.events.append(PackageEvent(title=title, description=description))


# ---------- Sesión ----------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya tiene sesión, no tiene sentido mostrar el login
    if current_user.is_authenticated:
        return redirect(url_for('suite.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Credenciales incorrectas. Verifique su correo y contraseña.', 'danger')
        elif user.role not in WEB_ROLES:
            flash('Esta cuenta solo puede ingresar desde la app.', 'danger')
        else:
            login_user(user, remember=request.form.get('remember') == '1')
            flash(f'Bienvenido a la Suite, {user.name}.', 'success')
            return redirect(url_for('suite.dashboard'))

    return render_template('suite/login.html')


@bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    # TO DO: Enviar el correo de recuperación de contraseña.
    if request.method == 'POST':
        flash('La recuperación por correo todavía no está configurada.', 'warning')
    return render_template('suite/recuperar.html')


@bp.route('/logout')
def logout():
    logout_user()
    flash('Ha cerrado sesión exitosamente.', 'info')
    return redirect(url_for('suite.login'))


# ---------- Dashboard ----------
@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    # Paquetes creados en cada uno de los últimos 6 meses y en los mismos meses del año anterior
    today = datetime.now()
    months, created, previous = [], [], []
    for back in range(5, -1, -1):
        year, month = today.year, today.month - back
        if month < 1:  # meses del año anterior
            year, month = year - 1, month + 12
        months.append(MONTHS[month - 1])
        created.append(count_created(year, month))
        previous.append(count_created(year - 1, month))

    # Paquetes por rango de peso (kg)
    weight_ranges = [(0, 5), (5, 8), (8, 10), (10, 100000)]
    weights = [
        Package.query.filter(Package.weight > low, Package.weight <= high).count()
        for low, high in weight_ranges
    ]

    # Cifras: total y por estado, con cuántos se crearon este mes
    counts = status_counts()
    start = month_start(today)
    this_month = dict(
        db.session.query(Package.status, func.count()).filter(Package.created_at >= start).group_by(Package.status)
    )
    stats = [
        ('peach', 'Total paquetes', 'i-box', sum(counts.values()), sum(this_month.values())),
        ('sky', 'Pendientes', 'i-pin', counts.get('pending', 0), this_month.get('pending', 0)),
        ('lilac', 'En ruta', 'i-bike', counts.get('picked_up', 0), this_month.get('picked_up', 0)),
        ('mint', 'Entregados', 'i-chart', counts.get('delivered', 0), this_month.get('delivered', 0)),
    ]

    # Datos para las gráficas (se envían a dashboard.js como JSON)
    chart_data = {'months': months, 'created': created, 'previous': previous, 'weights': weights}
    recent = Package.query.order_by(Package.id.desc()).limit(5).all()
    ranking = courier_deliveries()[:4]
    return render_template(
        'suite/dashboard.html', stats=stats, chart_data=chart_data, recent=recent, ranking=ranking
    )


def count_created(year, month):
    """Cantidad de paquetes creados en un mes."""
    start = datetime(year, month, 1)
    end = datetime(year + month // 12, month % 12 + 1, 1)
    return Package.query.filter(Package.created_at >= start, Package.created_at < end).count()


def courier_deliveries():
    """Entregas del mes de cada courier, de mayor a menor: [(nombre, total), ...]"""
    rows = (
        db.session.query(User.name, func.count(Package.id))
        .join(Package, Package.courier_id == User.id)
        .filter(Package.status == 'delivered', Package.delivered_at >= month_start(datetime.now()))
        .group_by(User.id, User.name)
        .order_by(func.count(Package.id).desc())
        .all()
    )
    return [(name, total) for name, total in rows]


# ---------- Paquetes ----------
def next_tracking_number():
    """Siguiente número de guía disponible: DX-000001, DX-000002, ..."""
    last = db.session.query(func.max(Package.tracking_number)).scalar()
    number = int(last[3:]) + 1 if last else 1
    return f'DX-{number:06d}'


def read_package_form():
    """Lee y valida el formulario de paquetes. Devuelve (datos, mensaje_de_error)."""
    form = request.form
    data = {field: form.get(field, '').strip() for field in PACKAGE_TEXT_FIELDS}
    data['is_urgent'] = form.get('is_urgent') == '1'

    # Peso y distancia: números dentro de un rango razonable
    try:
        data['weight'] = float(form.get('weight', ''))
        data['distance_km'] = float(form.get('distance_km') or 0)
    except ValueError:
        return data, 'El peso y la distancia deben ser números.'
    if not 0 < data['weight'] < 1000 or not 0 <= data['distance_km'] < 1000:
        return data, 'Ingrese un peso mayor que cero y una distancia válida.'

    if not all(data[field] for field in PACKAGE_REQUIRED_FIELDS):
        return data, 'Complete todos los datos del remitente y del destinatario.'

    # El courier es opcional, pero si viene tiene que existir
    data['courier_id'] = form.get('courier_id', type=int)
    if data['courier_id'] and not User.query.filter_by(id=data['courier_id'], role='courier').first():
        return data, 'El repartidor seleccionado no existe.'

    # Ubicaciones elegidas en el mapa (opcionales): latitud y longitud de origen y destino
    for point in ('origin', 'destination'):
        try:
            lat, lng = form.get(f'{point}_lat', '').strip(), form.get(f'{point}_lng', '').strip()
            data[f'{point}_lat'] = float(lat) if lat and lng else None
            data[f'{point}_lng'] = float(lng) if lat and lng else None
        except ValueError:
            return data, 'La ubicación seleccionada en el mapa no es válida.'
        lat, lng = data[f'{point}_lat'], data[f'{point}_lng']
        if lat is not None and not (CARTAGENA_BOUNDS[0][0] <= lat <= CARTAGENA_BOUNDS[1][0] and CARTAGENA_BOUNDS[0][1] <= lng <= CARTAGENA_BOUNDS[1][1]):
            return data, 'La ubicación seleccionada debe estar dentro de Cartagena.'
    return data, None


def package_form_page(package, values):
    """Muestra el formulario de paquetes (nuevo o edición)."""
    couriers = User.query.filter_by(role='courier').order_by(User.name).all()
    return render_template('suite/package_form.html', package=package, values=values, couriers=couriers)


@bp.route('/paquetes')
@login_required
def paquetes():
    # Filtros del listado (vienen en la URL: ?guia=...&estado=...&rango=...)
    tracking = request.args.get('guia', '').strip()
    status = request.args.get('estado', '')
    # Si se busca una guía concreta, se ignora el rango de fechas
    period = 'todo' if tracking else request.args.get('rango', '30')

    query = Package.query
    if tracking:
        query = query.filter(Package.tracking_number.ilike(f'%{tracking}%'))
    if status in STATUSES:
        query = query.filter_by(status=status)
    if period in ('7', '30'):
        query = query.filter(Package.created_at >= datetime.now() - timedelta(days=int(period)))
    elif period == 'mes':
        query = query.filter(Package.created_at >= month_start(datetime.now()))

    # Paginación (8 por página) con la librería de Flask-SQLAlchemy
    page = request.args.get('pagina', 1, type=int)
    pagination = query.order_by(Package.id.desc()).paginate(page=page, per_page=8, error_out=False)

    # Datos de la vista rápida (ventana emergente), uno por paquete de la página
    quick = {}
    for p in pagination.items:
        info = p.to_dict()
        info['courier'] = p.courier.name if p.courier else None
        info['detailUrl'] = url_for('suite.paquete', package_id=p.id)
        info['editUrl'] = url_for('suite.editar_paquete', package_id=p.id)
        quick[p.id] = info

    counts = status_counts()
    return render_template(
        'suite/paquetes.html',
        pagination=pagination,
        quick=quick,
        counts=counts,
        total=sum(counts.values()),
        tracking=tracking,
        status=status,
        period=period,
    )


@bp.route('/paquetes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_paquete():
    if request.method == 'POST':
        data, error = read_package_form()
        if error:
            flash(error, 'danger')
            return package_form_page(None, request.form.to_dict() | {'is_urgent': data['is_urgent']})

        # El número de guía lo asigna el sistema: el siguiente disponible
        package = Package(tracking_number=next_tracking_number(), **data)
        add_event(package, 'Guía generada', f'Registrada en la Suite por {current_user.name}.')
        db.session.add(package)
        try:
            db.session.commit()
        except IntegrityError:
            # Dos personas crearon una guía al mismo tiempo y el número se repitió
            db.session.rollback()
            flash('No se pudo asignar el número de guía. Inténtelo de nuevo.', 'danger')
            return package_form_page(None, request.form.to_dict())

        flash(f'Paquete {package.tracking_number} creado con éxito.', 'success')
        return redirect(url_for('suite.paquete', package_id=package.id))

    return package_form_page(None, {})


# Firma de quien recibió el paquete (la guarda la app al entregar)
@bp.route('/paquetes/<int:package_id>/firma')
@login_required
def firma(package_id):
    package = db.get_or_404(Package, package_id)
    if not package.signature:
        abort(404)
    return Response(package.signature, mimetype='image/png')


@bp.route('/paquetes/<int:package_id>')
@login_required
def paquete(package_id):
    package = db.get_or_404(Package, package_id)
    return render_template('suite/package.html', package=package, map_point=map_point(package))


# El manager y el administrador pueden editar paquetes
@bp.route('/paquetes/<int:package_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paquete(package_id):
    package = db.get_or_404(Package, package_id)

    if request.method == 'POST':
        data, error = read_package_form()
        new_status = request.form.get('status', '')
        if not error and new_status not in STATUSES:
            error = 'Seleccione un estado válido.'
        if error:
            flash(error, 'danger')
            return package_form_page(package, request.form.to_dict() | {'is_urgent': data['is_urgent']})

        # Si cambia el repartidor o el estado, queda registrado en el historial
        if data['courier_id'] != package.courier_id and data['courier_id']:
            add_event(package, 'Repartidor asignado', f'Asignado por {current_user.name}.')
        if new_status != package.status:
            package.status = new_status
            package.delivered_at = datetime.now() if new_status == 'delivered' else None
            if new_status != 'issue':
                package.issue_reason = None  # el motivo solo aplica mientras hay novedad
            add_event(package, STATUSES[new_status], f'Actualizado por {current_user.name}.')

        for field, value in data.items():
            setattr(package, field, value)
        db.session.commit()
        flash(f'Paquete {package.tracking_number} actualizado.', 'success')
        return redirect(url_for('suite.paquete', package_id=package.id))

    # GET: el formulario se llena con los datos actuales del paquete
    values = {field: getattr(package, field) for field in (*PACKAGE_TEXT_FIELDS, 'origin_lat', 'origin_lng', 'destination_lat', 'destination_lng', 'weight', 'distance_km', 'is_urgent', 'courier_id', 'status')}
    return package_form_page(package, values)


# Solo el administrador puede eliminar paquetes
@bp.route('/paquetes/<int:package_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_paquete(package_id):
    package = db.get_or_404(Package, package_id)
    tracking = package.tracking_number  # se guarda antes, porque luego el objeto ya no existe
    db.session.delete(package)
    db.session.commit()
    flash(f'Paquete {tracking} eliminado.', 'success')
    return redirect(url_for('suite.paquetes'))


# ---------- Usuarios: repartidores (courier) y managers ----------
def create_user_from_form(role):
    """Crea un usuario con los datos del formulario. Devuelve (usuario, mensaje_de_error)."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    # El teléfono solo es obligatorio para los repartidores
    if not name or '@' not in email or len(password) < 8 or (role == 'courier' and not phone):
        return None, 'Complete todos los campos. La contraseña debe tener mínimo 8 caracteres.'
    if User.query.filter_by(email=email).first():
        return None, 'Ya existe un usuario con ese correo.'

    user = User(name=name, email=email, role=role, phone=phone or None)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def update_user_from_form(user):
    """Actualiza un usuario con los datos del formulario. Devuelve un mensaje de error o None."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    if not name or '@' not in email or (user.role == 'courier' and not phone):
        return 'Complete el nombre, el correo y, en repartidores, el teléfono.'
    if password and len(password) < 8:
        return 'La nueva contraseña debe tener mínimo 8 caracteres.'
    other = User.query.filter_by(email=email).first()
    if other and other.id != user.id:
        return 'Ya existe un usuario con ese correo.'

    user.name = name
    user.email = email
    user.phone = phone or None
    if password:  # si se deja vacía, la contraseña no cambia
        user.set_password(password)
    db.session.commit()
    return None


@bp.route('/repartidores', methods=['GET', 'POST'])
@login_required
def repartidores():
    if request.method == 'POST':
        user, error = create_user_from_form('courier')
        flash(error or f'Repartidor {user.name} agregado correctamente.', 'danger' if error else 'success')
        return redirect(url_for('suite.repartidores'))

    couriers = User.query.filter_by(role='courier').order_by(User.name).all()

    # Entregas del mes de cada courier: {id_courier: total}
    deliveries = dict(
        db.session.query(User.id, func.count(Package.id))
        .join(Package, Package.courier_id == User.id)
        .filter(Package.status == 'delivered', Package.delivered_at >= month_start(datetime.now()))
        .group_by(User.id)
    )
    # Paquetes recogidos (en curso) de cada courier: {id_courier: total}; con alguno, está "en ruta"
    on_route = dict(
        db.session.query(Package.courier_id, func.count()).filter_by(status='picked_up').group_by(Package.courier_id)
    )
    # Paquetes asignados que todavía no se recogen: {id_courier: total}
    waiting = dict(
        db.session.query(Package.courier_id, func.count()).filter_by(status='pending').group_by(Package.courier_id)
    )
    return render_template(
        'suite/repartidores.html',
        couriers=couriers,
        waiting=waiting,
        deliveries=deliveries,
        on_route=on_route,
        monthly_goal=MONTHLY_GOAL,
        month_total=sum(deliveries.values()),
    )


# El manager y el administrador pueden editar repartidores
@bp.route('/repartidores/<int:courier_id>/editar', methods=['POST'])
@login_required
def editar_repartidor(courier_id):
    courier = User.query.filter_by(id=courier_id, role='courier').first_or_404()
    error = update_user_from_form(courier)
    flash(error or f'Repartidor {courier.name} actualizado correctamente.', 'danger' if error else 'success')
    return redirect(url_for('suite.repartidores'))


# Solo el administrador puede eliminar repartidores
@bp.route('/repartidores/<int:courier_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_repartidor(courier_id):
    # Solo se pueden borrar usuarios con rol courier (no un admin por la URL)
    courier = User.query.filter_by(id=courier_id, role='courier').first_or_404()
    name = courier.name
    # Sus paquetes quedan sin repartidor asignado
    Package.query.filter_by(courier_id=courier.id).update({'courier_id': None})
    db.session.delete(courier)
    db.session.commit()
    flash(f'Repartidor {name} eliminado correctamente.', 'success')
    return redirect(url_for('suite.repartidores'))


@bp.route('/managers', methods=['GET', 'POST'])
@admin_required
def managers():
    if request.method == 'POST':
        user, error = create_user_from_form('manager')
        flash(error or f'Manager {user.name} creado correctamente.', 'danger' if error else 'success')
        return redirect(url_for('suite.managers'))

    managers = User.query.filter_by(role='manager').order_by(User.name).all()
    return render_template('suite/managers.html', managers=managers)


@bp.route('/managers/<int:manager_id>/editar', methods=['POST'])
@admin_required
def editar_manager(manager_id):
    manager = User.query.filter_by(id=manager_id, role='manager').first_or_404()
    error = update_user_from_form(manager)
    flash(error or f'Manager {manager.name} actualizado correctamente.', 'danger' if error else 'success')
    return redirect(url_for('suite.managers'))


@bp.route('/managers/<int:manager_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_manager(manager_id):
    manager = User.query.filter_by(id=manager_id, role='manager').first_or_404()
    name = manager.name
    db.session.delete(manager)
    db.session.commit()
    flash(f'Manager {name} eliminado correctamente.', 'success')
    return redirect(url_for('suite.managers'))


# ---------- Perfil del usuario con sesión ----------
@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')

        other = User.query.filter_by(email=email).first()
        if not name or '@' not in email:
            flash('Ingrese su nombre y un correo válido.', 'danger')
        elif other and other.id != current_user.id:
            flash('Ya existe un usuario con ese correo.', 'danger')
        elif new and not current_user.check_password(current):
            flash('La contraseña actual no es correcta.', 'danger')
        elif new and len(new) < 8:
            flash('La nueva contraseña debe tener mínimo 8 caracteres.', 'danger')
        else:
            current_user.name = name
            current_user.email = email
            current_user.phone = phone or None
            if new:  # si se deja vacía, la contraseña no cambia
                current_user.set_password(new)
            db.session.commit()
            flash('Perfil actualizado correctamente.', 'success')
            return redirect(url_for('suite.perfil'))

    return render_template('suite/perfil.html')


# ---------- Mapa de paquetes ----------
# Muestra de dónde sale cada paquete y a dónde va (los que tienen ubicaciones en el mapa)
@bp.route('/mapa')
@login_required
def mapa():
    packages = (
        Package.query.filter(Package.origin_lat.isnot(None), Package.destination_lat.isnot(None))
        .order_by(Package.id.desc())
        .limit(500)
        .all()
    )
    return render_template('suite/mapa.html', points=[map_point(p) for p in packages])


# ---------- Reportes (solo administrador) ----------
REPORT_TYPES = {'paquetes': 'Paquetes', 'repartidores': 'Repartidores'}


def parse_date(text, default):
    try:
        return datetime.strptime(text, '%Y-%m-%d')
    except ValueError:
        return default


def build_report(kind, start, end, status):
    """Devuelve (columnas, filas) del reporte, con los paquetes creados entre dos fechas (ambas incluidas)."""
    in_range = (Package.created_at >= start, Package.created_at < end + timedelta(days=1))

    if kind == 'repartidores':
        columns = ['Repartidor', 'Asignados', 'Entregados', 'En ruta', 'Pendientes', 'Con novedad', 'Km entregados', 'Efectividad']
        rows = []
        for courier in User.query.filter_by(role='courier').order_by(User.name):
            mine = Package.query.filter(Package.courier_id == courier.id, *in_range).all()
            delivered = [p for p in mine if p.status == 'delivered']
            rows.append([
                courier.name,
                len(mine),
                len(delivered),
                sum(p.status == 'picked_up' for p in mine),
                sum(p.status == 'pending' for p in mine),
                sum(p.status == 'issue' for p in mine),
                round(sum(p.distance_km for p in delivered), 1),
                f'{round(100 * len(delivered) / len(mine)) if mine else 0}%',
            ])
        return columns, rows

    columns = ['Guía', 'Fecha', 'Estado', 'Remitente', 'Origen', 'Destinatario', 'Destino', 'Repartidor', 'Peso (kg)', 'Km', 'Urgente']
    query = Package.query.filter(*in_range)
    if status in STATUSES:
        query = query.filter_by(status=status)
    rows = [
        [
            p.tracking_number, p.created_at.strftime('%Y-%m-%d'), p.status_label,
            p.sender_name, p.origin_address, p.recipient_name, p.destination_address,
            p.courier.name if p.courier else 'Sin asignar', p.weight, p.distance_km, 'Sí' if p.is_urgent else 'No',
        ]
        for p in query.order_by(Package.created_at.desc())
    ]
    return columns, rows


@bp.route('/reportes')
@admin_required
def reportes():
    kind = request.args.get('tipo', 'paquetes')
    if kind not in REPORT_TYPES:
        kind = 'paquetes'
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = parse_date(request.args.get('desde', ''), today - timedelta(days=29))
    end = parse_date(request.args.get('hasta', ''), today)
    status = request.args.get('estado', '')
    columns, rows = build_report(kind, start, end, status)

    # Descarga en CSV (con BOM para que Excel respete las tildes)
    if request.args.get('descargar'):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        writer.writerows(rows)
        return Response(
            '\ufeff' + buffer.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=reporte-{kind}-{start:%Y%m%d}-{end:%Y%m%d}.csv'},
        )

    return render_template(
        'suite/reportes.html', kind=kind, types=REPORT_TYPES, columns=columns, rows=rows[:50], total=len(rows),
        start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), status=status,
    )

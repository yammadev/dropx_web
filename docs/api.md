# API de DropX

Todas las rutas empiezan con `/api` y responden JSON. La autenticación usa tokens JWT.

URL base en pruebas: `http://127.0.0.1:5000`
(en el emulador de Android: `http://10.0.2.2:5000`).

## Autenticación

### `POST /api/auth/login`

Inicia sesión. Sirve para los tres roles (`admin`, `manager` y `courier`).

Recibe:

```json
{ "email": "courier@dropx.com", "password": "su-clave" }
```

Responde `200`:

```json
{
  "token": "eyJhbGciOi...",
  "user": { "id": 3, "name": "Jhon Doe", "email": "courier@dropx.com", "role": "courier" }
}
```

| Código | Cuándo | Respuesta |
|---|---|---|
| `400` | Falta el correo o la contraseña | `{"message": "El correo y la contraseña son obligatorios"}` |
| `401` | Correo o contraseña incorrectos | `{"message": "Correo o contraseña incorrectos"}` |

### `GET /api/auth/me`

Devuelve el usuario dueño del token. Requiere el header `Authorization: Bearer <token>`.

Responde `200`:

```json
{ "user": { "id": 3, "name": "Jhon Doe", "email": "courier@dropx.com", "role": "courier" } }
```

| Código | Cuándo | Respuesta |
|---|---|---|
| `401` | Falta el token | `{"message": "Falta el token de acceso"}` |
| `401` | El token no es válido | `{"message": "El token no es válido"}` |
| `401` | El token expiró | `{"message": "El token expiró, inicia sesión de nuevo"}` |

El token dura las horas indicadas en `JWT_EXPIRES_HOURS` (por defecto, 168, es decir, 7 días) y guarda el id y el rol del usuario.

## Paquetes del repartidor

Requieren el header `Authorization: Bearer <token>`. Devuelven solo los paquetes asignados al usuario del token.

Estados (`status`): `pending` (pendiente), `picked_up` (recogido), `delivered` (entregado) e `issue` (con novedad).
En la app: `pending` es pendiente, `picked_up` es en tránsito, `delivered` es entregado e `issue` es problema.

### `GET /api/packages`

Lista los paquetes asignados, los urgentes primero. Filtro opcional por estado: `GET /api/packages?status=pending`.

Responde `200`:

```json
{
  "packages": [
    {
      "id": 1,
      "number": "DX-000001",
      "weightKg": 3.2,
      "distanceKm": 4.1,
      "isUrgent": true,
      "status": "pending",
      "originAddress": "Calle 30 #12-45",
      "destinationAddress": "Getsemaní",
      "originLat": 10.4105,
      "originLng": -75.5340,
      "destinationLat": 10.4229,
      "destinationLng": -75.5460,
      "issueReason": null,
      "sender": { "name": "Tienda Mar", "document": null, "phone": "300 000 0000" },
      "receiver": { "name": "Carolina Díaz", "document": null, "phone": "300 111 1111" },
      "updatedAt": "2026-11-06T10:30:00"
    }
  ]
}
```

| Código | Cuándo | Respuesta |
|---|---|---|
| `400` | El estado del filtro no existe | `{"message": "El estado no es válido"}` |
| `401` | Falta el token, no es válido o expiró | ver `/api/auth/me` |

Las coordenadas (`originLat`, `originLng`, `destinationLat`, `destinationLng`) son `null` si la guía no tiene ubicaciones elegidas en el mapa. `issueReason` solo trae valor cuando el estado es `issue`.

### `GET /api/packages/<id>`

Devuelve un paquete (`{"package": {...}}`) con los mismos campos. Responde `404` (`{"message": "Paquete no encontrado"}`) si no existe o no está asignado al usuario.

### `PATCH /api/packages/<id>/status`

Cambia el estado de un paquete asignado al usuario del token y registra el movimiento en el historial.

Recibe:

```json
{ "status": "picked_up" }
```

Campos adicionales:

| Campo | Cuándo | Descripción |
|---|---|---|
| `reason` | Obligatorio si `status` es `issue` | Motivo de la novedad (máximo 100 caracteres). |
| `signature` | Opcional si `status` es `delivered` | Firma de quien recibe: imagen PNG en base64 (máximo 500 KB). Se guarda en la base de datos (columna `signature` del paquete) y se ve en el detalle del paquete de la Suite. |

Cambios permitidos:

| Estado actual | Puede pasar a |
|---|---|
| `pending` | `picked_up`, `issue` |
| `picked_up` | `delivered`, `issue` |
| `issue` | `picked_up` |
| `delivered` | ninguno |

Responde `200` con el paquete actualizado (`{"package": {...}}`).

| Código | Cuándo | Respuesta |
|---|---|---|
| `400` | El estado no existe | `{"message": "El estado no es válido"}` |
| `400` | Novedad sin motivo | `{"message": "Indique el motivo de la novedad"}` |
| `400` | La firma no es un PNG válido | `{"message": "La firma no es válida"}` |
| `404` | El paquete no existe o no está asignado al usuario | `{"message": "Paquete no encontrado"}` |
| `409` | El cambio no está permitido | `{"message": "No se puede pasar de \"Entregado\" a \"Recogido\""}` |

## Probar en Postman

1. Inicie el servidor: `flask --app app run`.
2. Cree una petición `POST` a `http://127.0.0.1:5000/api/auth/login`. En **Body**, elija **raw** y **JSON**, y escriba:
   `{ "email": "courier@dropx.com", "password": "su-clave" }`
3. Copie el valor de `token` de la respuesta.
4. Cree una petición `GET` a `http://127.0.0.1:5000/api/packages`. En **Authorization**, elija **Bearer Token** y pegue el token.
5. Para filtrar, agregue en **Params** la clave `status` con un valor como `pending`.

Si la lista llega vacía, asigne paquetes al repartidor desde la Suite (Paquetes, Editar, Repartidor).

## Probar desde la terminal

```powershell
$body = @{ email = 'courier@dropx.com'; password = 'su-clave' } | ConvertTo-Json
$res = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/auth/login -ContentType 'application/json' -Body $body
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/auth/me -Headers @{ Authorization = "Bearer $($res.token)" }
```

## Pendientes

- CORS, si la app Flutter se prueba en Chrome.

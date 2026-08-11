# Simulated Position Push API

Pushes a simulated GPS position (latitude / longitude / rotation) onto a single vehicle — used by the tracking/simulation systems and external ticketer devices to report where a vehicle is.

- **Endpoint:** `POST /api/trips/vehicle/<vehicle_id>/simulate/`
- **Rate limit:** 30 requests per minute per IP
- **Auth:** Session key (ticketer-code system) — see below
- **Base URL note:** paths below are relative to the site root (e.g. `https://yourdomain.com/api/trips/vehicle/123/simulate/`)

---

## 1. Authentication

The endpoint uses the same session-key mechanism as the ticketer code system. You must first log in to obtain a session key, then send that key on every request.

### 1a. Get a session key

`POST /api/user/`

Login using either of these JSON body shapes:

**Option A — user ID + ticketer code:**

```json
{
  "user_id": 1,
  "code": "123456"
}
```

**Option B — username + password:**

```json
{
  "username": "ej",
  "password": "hunter2"
}
```

**Response (200):**

```json
{
  "id": 1,
  "username": "ej",
  "ticketer_code": "123456",
  "session_key": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Note: issuing a new `get_user_profile` call deletes all previous session keys for that user and generates a fresh one.

### 1b. Send the session key

Every request to the simulate endpoint needs the session key, supplied either:

- as the JSON field `session_key`, or
- as an `Authorization` header: `Authorization: SessionKey <key>`

---

## 2. Request

### URL
```
POST /api/trips/vehicle/<vehicle_id>/simulate/
```

`vehicle_id` is the numeric vehicle ID (seen in the address bar of the vehicle edit page, e.g. `https://yourdomain.com/operator/<slug>/vehicle/edit/171541/`).

### Headers
```
Content-Type: application/json
Authorization: SessionKey 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
```

### Body (JSON)

| Field       | Type    | Required | Description                                       |
|-------------|---------|----------|---------------------------------------------------|
| `lat`       | number  | Yes      | Latitude, between `-90` and `90`                  |
| `lon`       | number  | Yes      | Longitude, between `-180` and `180`               |
| `rotation`  | number  | No       | Compass heading in degrees, between `0` and `360`. Omitted → keeps the vehicle's current `sim_heading` |
| `vehicle_id`| int     | No       | Alternative to the URL path (`vehicle_id` in URL wins) |
| `session_key`| string | No      | Alternative to the `Authorization` header          |

**Example:**
```json
{
  "lat": 52.630886,
  "lon": -2.460367,
  "rotation": 124.5
}
```

---

## 3. Response

**Success (200):**
```json
{
  "success": true,
  "vehicle_id": 171541,
  "lat": 52.630886,
  "lon": -2.460367,
  "rotation": 124.5,
  "updated_at": "2026-08-11T14:23:45.123456+00:00"
}
```

The vehicle's `sim_lat`, `sim_lon`, `sim_heading` and `updated_at` fields are updated and saved.

---

## 4. Errors

| Status | Body `error`                          | When                                            |
|--------|---------------------------------------|-------------------------------------------------|
| 405    | `Only POST method is allowed`         | Non-POST request                               |
| 400    | `Invalid JSON`                        | Body is not valid JSON                          |
| 400    | `Missing vehicle_id`                  | No ID in URL or body                            |
| 401    | `Missing session_key`                 | No session key supplied                         |
| 401    | `Invalid session key`                 | Session key does not match any `UserKeys` row   |
| 403    | `Permission denied`                   | User does not own the vehicle's operator (or loan operator) |
| 404    | `Vehicle not found`                   | Vehicle ID does not exist                       |
| 400    | `lat and lon are required numeric fields` | `lat`/`lon` missing or not numeric           |
| 400    | `lat must be between -90 and 90`      | Latitude out of range                           |
| 400    | `lon must be between -180 and 180`    | Longitude out of range                          |
| 400    | `rotation must be numeric`            | Rotation not numeric                            |
| 400    | `rotation must be between 0 and 360`  | Rotation out of range                           |

---

## 5. Permissions

Only the owner of the operator a vehicle belongs to **or** is loaned to may push a position:

- `vehicle.operator.owner == user` → allowed
- `vehicle.loan_operator.owner == user` → allowed
- otherwise → `403 Permission denied`

---

## 6. Example: curl

```bash
# 1. Log in and grab the session key
curl -X POST https://yourdomain.com/api/user/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "code": "123456"}'

# 2. Push a position using the Authorization header
curl -X POST https://yourdomain.com/api/trips/vehicle/171541/simulate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: SessionKey 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08" \
  -d '{"lat": 52.630886, "lon": -2.460367, "rotation": 124.5}'
```

---

## 7. Example: Python

```python
import requests

BASE = "https://yourdomain.com"

# 1. Log in
r = requests.post(f"{BASE}/api/user/", json={"user_id": 1, "code": "123456"})
r.raise_for_status()
key = r.json()["session_key"]

# 2. Push a position
r = requests.post(
    f"{BASE}/api/trips/vehicle/171541/simulate/",
    headers={"Content-Type": "application/json",
             "Authorization": f"SessionKey {key}"},
    json={"lat": 52.630886, "lon": -2.460367, "rotation": 124.5},
)
print(r.status_code, r.json())
```

---

## 8. Implementation reference

- View: `tracking/views.py` → `push_sim_position`
- URL: `api/urls.py` line 69, name `push_sim_position`, wrapped in `ratelimit(key='ip', method='POST', rate='30/m')`
- Session key storage: `main/models.py` → `UserKeys`
- Login helper: `main/views.py` → `get_user_profile` (registered as `GET /api/user/` in `api/urls.py`; the view itself only accepts `POST`)
- Fields written on the vehicle (`fleet` model): `sim_lat`, `sim_lon`, `sim_heading`, `updated_at`
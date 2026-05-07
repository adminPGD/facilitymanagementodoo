# RUA Facility Portal API — Documentation

## Overview

REST API layer for the Next.js Facility Management Portal.
Module: `rua_facility_portal_api`

## Authentication

All protected endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Login

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "login": "admin",
  "password": "Demo@12345",
  "db": "facility_rua"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "user": {
      "id": 2,
      "name": "Administrator",
      "login": "admin",
      "email": "admin@rua.edu.sa",
      "role": "admin",
      "national_id": null,
      "university_id": null,
      "department": null,
      "college": null,
      "avatar_url": "/web/image/res.users/2/avatar_128"
    }
  },
  "message": "Login successful",
  "errors": []
}
```

### Refresh Token

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### Get Current User

```
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

---

## Standard Response Format

### Success
```json
{
  "success": true,
  "data": { ... },
  "message": "...",
  "errors": [],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### Error
```json
{
  "success": false,
  "data": null,
  "message": "Human-readable error",
  "errors": [
    { "field": "description", "message": "description is required" }
  ]
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 500 | Server error |

---

## Pagination

List endpoints support:

| Param | Default | Max | Description |
|-------|---------|-----|-------------|
| `page` | 1 | - | Page number |
| `limit` | 20 | 100 | Items per page |
| `search` | - | - | Search text (description/title) |
| `sort` | `create_date desc` | - | Sort order |

Response includes `meta` with pagination info.

---

## Roles

| Portal Role | Odoo facility_role | Access |
|-------------|-------------------|--------|
| `user` | student | Own requests only |
| `faculty` | faculty | Own requests only |
| `employee` | employee | Own requests only |
| `technician` | technician | Own assigned work orders |
| `manager` | facility_manager, facility_supervisor, management | All requests and work orders |
| `contractor` | contractor | Own assigned work orders |
| `admin` | superuser | Full access |

---

## Endpoints

### Campus

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/campus` | ✅ | List campuses |
| GET | `/api/v1/buildings?campus_id=` | ✅ | List buildings |
| GET | `/api/v1/floors?building_id=` | ✅ | List floors |
| GET | `/api/v1/spaces?floor_id=&building_id=&space_type=` | ✅ | List spaces |
| GET | `/api/v1/spaces/<id>/status` | ✅ | Space status |
| GET | `/api/v1/request-categories` | ✅ | List categories |

### Requests

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/requests` | ✅ | List own requests |
| GET | `/api/v1/requests/<id>` | ✅ | Request detail |
| POST | `/api/v1/requests` | ✅ | Create request |
| POST | `/api/v1/requests/<id>/update` | ✅ | Update draft request |
| POST | `/api/v1/requests/<id>/comment` | ✅ | Add comment |
| POST | `/api/v1/requests/<id>/cancel` | ✅ | Cancel request |
| POST | `/api/v1/requests/<id>/reopen` | ✅ | Reopen request |
| POST | `/api/v1/requests/<id>/rating` | ✅ | Rate request |
| POST | `/api/v1/requests/<id>/attachments` | ✅ | Upload files |
| GET | `/api/v1/reports/dashboard` | ✅ | User dashboard KPIs |

### Manager

| Method | URL | Auth | Role |
|--------|-----|------|------|
| GET | `/api/v1/manager/dashboard` | ✅ | manager |
| GET | `/api/v1/manager/requests` | ✅ | manager |
| GET | `/api/v1/manager/requests/<id>` | ✅ | manager |
| GET | `/api/v1/manager/work-orders` | ✅ | manager |
| GET | `/api/v1/manager/work-orders/<id>` | ✅ | manager |

### Technician

| Method | URL | Auth | Role |
|--------|-----|------|------|
| GET | `/api/v1/technician/dashboard` | ✅ | any |
| GET | `/api/v1/technician/work-orders` | ✅ | any |
| GET | `/api/v1/technician/work-orders/<id>` | ✅ | assigned |
| POST | `/api/v1/technician/work-orders/<id>/action` | ✅ | assigned |

Actions: `accept`, `start`, `pause`, `resume`, `complete`

### Contractor

| Method | URL | Auth | Role |
|--------|-----|------|------|
| GET | `/api/v1/contractor/dashboard` | ✅ | any |
| GET | `/api/v1/contractor/work-orders` | ✅ | any |
| GET | `/api/v1/contractor/work-orders/<id>` | ✅ | own contractor |

### Notifications

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/notifications?page=` | ✅ | List notifications |
| POST | `/api/v1/notifications/<id>/read` | ✅ | Mark one read |
| POST | `/api/v1/notifications/mark-read` | ✅ | Mark batch read |
| POST | `/api/v1/notifications/read-all` | ✅ | Mark all read |

---

## File Upload

```
POST /api/v1/requests/<id>/attachments
Authorization: Bearer <token>
Content-Type: multipart/form-data

Field name: "files" (multiple)
```

### Limits
- Max file size: **10 MB**
- Max files per upload: **5**
- Allowed: jpg, jpeg, png, gif, pdf, doc, docx, xls, xlsx

---

## Create Request Payload

```json
{
  "request_type": "maintenance_report",
  "description": "HVAC not working in Drawing Studio",
  "priority": "high",
  "risk_level": "low",
  "campus_id": 1,
  "building_id": 1,
  "floor_id": 1,
  "space_id": 1,
  "asset_id": 1,
  "category_id": 1
}
```

### Request Types
`maintenance_report`, `observation`, `service_request`, `event_preparation`, `safety_report`, `cleaning_request`, `permit_request`

---

## Configuration

### JWT Secret
Set via **one** of (in priority order):
1. Odoo System Parameter: `rua_facility.jwt_secret`
2. Environment variable: `RUA_JWT_SECRET`
3. Fallback (development only — **not** for production)

### CORS Origins
Currently `cors='*'` on all routes (Odoo route-level limitation).
Portal should use Next.js rewrites to proxy API calls, avoiding CORS entirely.

---

## Security Notes

- JWT tokens expire in 24 hours; refresh tokens in 30 days
- Token type (`access` vs `refresh`) is validated — cannot use refresh token as access token
- `requester_id` is always set to the authenticated user — cannot be overridden
- `sudo()` is used only where portal users lack model-level create/write access:
  - `authenticate()` during login
  - `facility.request.create()` — requester_id hardcoded to current user
  - `facility.rating.create()` — rated_by hardcoded to current user
  - `ir.attachment.create()` — res_model/res_id hardcoded to facility.request
  - `mail.notification` read status updates
- File uploads validated for size, extension, and MIME type
- Login attempts logged with IP address
- Generic "Invalid credentials" message — does not reveal user existence

### Missing Models (Not Available)
These endpoints are **not** implemented because the models don't exist:
- `GET /api/v1/contractor/contracts` — no `facility.contract` model
- `GET /api/v1/manager/contracts` — no `facility.contract` model
- `GET /api/v1/manager/sustainability` — no sustainability model

### TODO
- [ ] Rate limiting on login endpoint (IP-based throttling)
- [ ] JWT token blacklist for logout (currently stateless)
- [ ] Dynamic CORS configuration via ir.config_parameter

# API Contracts

## Auth Service Endpoints

### `POST /api/auth/register`

Request JSON:

```json
{
  "displayName": "string",
  "email": "string (email)",
  "password": "string (min 8, letters and numbers)",
  "orgId": "string | null"
}
```

Success response `201`:

```json
{
  "token": "jwt-string",
  "user": {
    "id": "string",
    "displayName": "string",
    "email": "string",
    "role": 1,
    "type": 1,
    "active": true,
    "orgId": "string | null",
    "createdAt": "ISO-8601 datetime",
    "updatedAt": "ISO-8601 datetime | null",
    "role_name": "ADMIN | USER",
    "type_name": "VESSEL_OPERATOR | POWER_OPERATOR"
  },
  "message": "Registration successful"
}
```

Error responses:

- `400`: missing required field, invalid email, weak password
- `409`: email already registered
- `500`: registration failure

### `POST /api/auth/login`

Request JSON:

```json
{
  "email": "string (email)",
  "password": "string"
}
```

Success response `200`:

```json
{
  "token": "jwt-string",
  "user": {
    "id": "string",
    "displayName": "string",
    "email": "string",
    "role": 1,
    "type": 1,
    "active": true,
    "orgId": "string | null",
    "createdAt": "ISO-8601 datetime",
    "updatedAt": "ISO-8601 datetime | null",
    "role_name": "ADMIN | USER",
    "type_name": "VESSEL_OPERATOR | POWER_OPERATOR"
  },
  "expires_in": 86400
}
```

Error responses:

- `400`: missing email or password
- `401`: invalid credentials or deactivated account
- `500`: login failure

### `POST /api/auth/verify-token`

Request headers:

- `Authorization: Bearer <jwt>`

Success response `200`:

```json
{
  "user": {
    "id": "string",
    "displayName": "string",
    "email": "string",
    "role": 1,
    "type": 1,
    "active": true,
    "orgId": "string | null",
    "createdAt": "ISO-8601 datetime",
    "updatedAt": "ISO-8601 datetime | null",
    "role_name": "ADMIN | USER",
    "type_name": "VESSEL_OPERATOR | POWER_OPERATOR"
  },
  "valid": true
}
```

Error responses:

- `401`: no/invalid/expired token, deactivated account
- `404`: token user not found
- `500`: verification failure

### `POST /api/auth/logout`

Request: no body required.

Success response `200`:

```json
{
  "message": "Logged out successfully"
}
```

Notes:

- JWT is stateless; logout is a client-side token removal action.

## Auth Error Shape

Error JSON schema (all auth endpoints):

```json
{
  "error": "string",
  "details": "string (optional)"
}
```

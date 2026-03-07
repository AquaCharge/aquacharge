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

## DR Event Eligibility Endpoints

### `GET /api/drevents/{eventId}/eligibility`

Evaluate vessel eligibility for a DR event based on vessel status, distance to station,
charger compatibility, forecasted SOC, available battery capacity, and schedule compatibility.

Query parameters:

- `includeIneligible` (`true|false`, default `false`): include ineligible vessels with rejection reasons.

Success response `200`:

```json
{
  "eventId": "string",
  "stationId": "string",
  "totalVesselsEvaluated": 0,
  "eligibleCount": 0,
  "evaluationDurationMs": 0.0,
  "vessels": [
    {
      "vesselId": "string",
      "displayName": "string",
      "eligible": true,
      "reasons": [],
      "distanceMeters": 0.0,
      "distanceKm": 0.0,
      "rangeMeters": 0.0,
      "currentSoc": 0.0,
      "forecastedSoc": 0.0,
      "kwhPerKm": 0.2,
      "availableBatteryKwh": 0.0,
      "requiredEnergyPerVesselKwh": 0.0,
      "scheduleCompatible": true,
      "minimumSoc": 20.0,
      "chargerType": "string"
    }
  ]
}
```

Forecast formula:

- `forecastedSoc = currentSoc - (distanceKm * kwhPerKm)`

Schedule compatibility rules:

- If provided, vessel `availableFrom|availableStart` must be <= event `startTime`.
- If provided, vessel `availableUntil|availableEnd` must be >= event `endTime`.

Battery capacity rules:

- `availableBatteryKwh = vesselCapacityKwh * (forecastedSoc / 100)`
- `requiredEnergyPerVesselKwh` uses event `details.requiredEnergyPerVesselKwh`, or falls back to `targetEnergyKwh / maxParticipants`.

Error responses:

- `400`: invalid request parameters or event missing `stationId`
- `404`: DR event or station not found
- `500`: eligibility evaluation failed

## DR Event Eligibility Error Shape

Error JSON schema:

```json
{
  "error": "string",
  "details": "string (optional)"
}
```

## DR Events Endpoints

### `GET /api/drevents`

Query parameters:

- `status` (optional): filter by event status string.

Success response `200`:

```json
[
  {
    "id": "string",
    "stationId": "string",
    "pricePerKwh": 0.0,
    "targetEnergyKwh": 0.0,
    "maxParticipants": 0,
    "startTime": "ISO-8601 datetime",
    "endTime": "ISO-8601 datetime",
    "status": "Created",
    "details": {}
  }
]
```

### `POST /api/drevents`

Request JSON:

```json
{
  "stationId": "string",
  "pricePerKwh": 0.0,
  "targetEnergyKwh": 0.0,
  "maxParticipants": 0,
  "startTime": "ISO-8601 datetime",
  "endTime": "ISO-8601 datetime",
  "details": {}
}
```

Success response `201`: created DREvent object.

Error responses:

- `400`: missing required field or invalid datetime
- `401`: missing/invalid auth token
- `403`: non-admin user
- `500`: creation failure

## Booking Service Rules

The booking API is backed by a service-layer business rule engine (`BookingService`).

### Validation rules

- Required fields for create: `userId`, `vesselId`, `stationId`, `startTime`, `endTime`, `chargerType`.
- Datetimes must be ISO-8601.
- `endTime` must be strictly after `startTime`.

### Conflict rules

- A booking conflicts if:
  - same `stationId`, and
  - existing booking status is `Pending` or `Confirmed`, and
  - booking windows overlap (`not (newEnd <= existingStart or newStart >= existingEnd)`).

Conflict response:

- `409`: `{ "error": "Time slot conflicts with existing booking" }`

### Status transition rules

- Cancel is blocked for `Completed` bookings.
- Status values are validated against `BookingStatus`.

### Upcoming bookings filter

- `GET /api/bookings/upcoming?userId=...` includes only:
  - bookings owned by `userId`,
  - `startTime` after current UTC time,
  - status in `Pending` or `Confirmed`.

## Contract Service Rules

The contracts API is backed by a service layer (`ContractService`) and follows the
existing `Contract` object model fields/status values.

### Validation rules

- Required fields for create: `vesselId`, `drEventId`, `vesselName`,
  `energyAmount`, `pricePerKwh`, `startTime`, `endTime`, `terms`.
- Datetimes must be ISO-8601.
- `endTime` must be strictly after `startTime`.
- `bookingId` is optional and normalized from blank string to `null`.

### Derived fields

- `totalValue = energyAmount * pricePerKwh` on create.

### Status transition rules

- Update accepts only values in `ContractStatus`.
- Cancel endpoint allows only contracts currently in `pending`.
- Complete endpoint allows only contracts currently in `pending` or `active`.

### Filtering/sorting rules

- `GET /api/contracts` supports `status` and `vesselId` filters.
- Results are sorted by `createdAt` descending (newest first).

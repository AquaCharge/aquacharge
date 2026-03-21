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
    "currentVesselId": "string | null",
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
    "currentVesselId": "string | null",
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
    "currentVesselId": "string | null",
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

### `GET /api/auth/me`

Request headers:

- `Authorization: Bearer <jwt>`

Success response `200`: same user shape as login/verify-token, including optional `currentVesselId` (string or null).

Error responses:

- `401`: no/invalid/expired token, deactivated account
- `404`: user not found
- `500`: verification failure

### `PATCH /api/auth/me`

Update current user profile (e.g. current vessel for VO dashboard).

Request headers:

- `Authorization: Bearer <jwt>`

Request JSON:

```json
{
  "currentVesselId": "string | null"
}
```

- `null` or omitted or empty string clears the current vessel.

Success response `200`: updated user object (same shape as GET /api/auth/me).

Validation:

- If `currentVesselId` is non-null, the authenticated user must own that vessel (vessel’s `userId` must match the caller). Otherwise responds `403` with message "Vessel not found or you do not own this vessel".

Error responses:

- `401`: authentication required
- `403`: vessel not owned by user
- `404`: user not found
- `500`: update failure

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
- Eligibility resolves `currentSoc` from latest measurement telemetry first, then `vessel.currentSoc`, then derives it from `(capacity / maxCapacity) * 100` when telemetry is missing.

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

## Vessels

- Model fields: `chargerType` (string), `capacity` (float, kWh), `maxCapacity` (float, kWh).
- Validation: `capacity` must never exceed `maxCapacity` on create or update.
- Required fields for create: `userId`, `displayName`, `vesselType`, `chargerType`, `capacity`, `maxCapacity`.
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

Notes:

- Creating a DR event does **not** create a contract.
- Contracts are created later in the participation/acceptance flow.

Error responses:

- `400`: missing required field or invalid datetime
- `401`: missing/invalid auth token
- `403`: non-admin user
- `500`: creation failure

### `PUT /api/drevents/{eventId}`

Update an existing DR event, including lifecycle transitions.

Request JSON:

```json
{
  "status": "Dispatched",
  "pricePerKwh": 0.0,
  "targetEnergyKwh": 0.0,
  "maxParticipants": 0,
  "startTime": "ISO-8601 datetime",
  "endTime": "ISO-8601 datetime",
  "details": {}
}
```

Success response `200`: updated DREvent object.

Lifecycle transition rules:

- Primary lifecycle: `Created -> Dispatched -> Accepted -> Committed -> Active -> Completed -> Settled -> Archived`
- Existing schema side-state: `Cancelled`
- Allowed cancel transitions: `Created|Dispatched|Accepted|Committed|Active -> Cancelled`
- Same-status updates are allowed.
- Invalid transitions return `400`.

### `GET /api/drevents/monitoring`

Power-operator monitoring snapshot for the dashboard.

Query parameters:

- `eventId` (optional): filter to a specific DR event
- `region` (optional): substring match against station `city`, `provinceOrState`, or `country`
- `periodHours` (optional, default `24`): lookback window in hours, clamped to `1..168`

Success response `200`:

```json
{
  "filters": {
    "eventId": "string | null",
    "region": "string",
    "periodHours": 24
  },
  "selectedEvent": {
    "id": "string",
    "stationId": "string",
    "status": "Active",
    "targetEnergyKwh": 0.0,
    "startTime": "ISO-8601 datetime",
    "endTime": "ISO-8601 datetime",
    "regionLabel": "string"
  },
  "summary": {
    "totalEnergyDeliveredKwh": 0.0,
    "progressPercent": 0.0,
    "activeVessels": 0,
    "eventStatus": "Active",
    "targetEnergyKwh": 0.0
  },
  "vesselRates": [
    {
      "vesselId": "string",
      "contractId": "string | null",
      "dischargeRateKw": 0.0,
      "currentSoc": 0.0,
      "timestamp": "ISO-8601 datetime"
    }
  ],
  "vesselCurve": [
    {
      "vesselId": "string",
      "contractId": "string | null",
      "currentSoc": 0.0,
      "latestDischargeRateKw": 0.0,
      "latestTimestamp": "ISO-8601 datetime | null",
      "points": [
        {
          "timestamp": "ISO-8601 datetime",
          "energyDischargedKwh": 0.0,
          "cumulativeEnergyDischargedKwh": 0.0,
          "v2gContributionKw": 0.0
        }
      ]
    }
  ],
  "loadCurve": [
    {
      "timestamp": "ISO-8601 datetime",
      "energyDischargedKwh": 0.0,
      "cumulativeEnergyDischargedKwh": 0.0,
      "v2gContributionKw": 0.0,
      "gridLoadWithoutV2GKw": null,
      "gridLoadWithV2GKw": null
    }
  ],
  "baselineAvailable": false,
  "availableEvents": [
    {
      "id": "string",
      "stationId": "string",
      "status": "Active",
      "startTime": "ISO-8601 datetime",
      "endTime": "ISO-8601 datetime",
      "targetEnergyKwh": 0.0,
      "regionLabel": "string"
    }
  ],
  "empty": false,
  "updatedAt": "ISO-8601 datetime"
}
```

Monitoring rules:

- `totalEnergyDeliveredKwh` is the sum of measurement `energyKwh` values in the selected window
- `vesselRates` use the latest measurement per vessel in the selected window
- `vesselRates[].contractId` comes from measurement telemetry only and is not a DR event field
- `vesselCurve` provides a per-vessel time series derived from the same measurement window for dashboard filtering
- `loadCurve[].energyDischargedKwh` and `vesselCurve[].points[].energyDischargedKwh` represent discharged energy per time bucket
- `loadCurve[].cumulativeEnergyDischargedKwh` and `vesselCurve[].points[].cumulativeEnergyDischargedKwh` represent cumulative discharged energy over the selected window
- `progressPercent = totalEnergyDeliveredKwh / selectedEvent.targetEnergyKwh * 100`
- `loadCurve` is measurement-backed V2G contribution only; baseline grid load is not currently available in the schema and returns `null`
- Empty datasets return a successful snapshot with `empty = true`

### `GET /api/drevents/analytics`

Historical analytics snapshot for power operator trend dashboards.

Query parameters:

- `eventId` (optional): filter to a specific DR event
- `region` (optional): substring match against station `city`, `provinceOrState`, or `country`
- `periodHours` (optional, default `168`): historical lookback window in hours, clamped to `1..720`
- `grain` (optional, default `day`): rollup granularity (`hour` or `day`)

Success response `200`:

```json
{
  "filters": {
    "eventId": "string | null",
    "region": "string",
    "periodHours": 168,
    "grain": "day"
  },
  "summary": {
    "totalEnergyDischargedKwh": 0.0,
    "averagePowerKw": 0.0,
    "peakPowerKw": 0.0,
    "completionRatePercent": 0.0,
    "participationRatePercent": 0.0,
    "eventsConsidered": 0,
    "contractsConsidered": 0,
    "baselineAvailable": false
  },
  "selectedEvent": {
    "id": "string",
    "stationId": "string",
    "status": "Active",
    "targetEnergyKwh": 0.0,
    "startTime": "ISO-8601 datetime",
    "endTime": "ISO-8601 datetime",
    "regionLabel": "string"
  } | null,
  "timeSeries": [
    {
      "timestamp": "ISO-8601 datetime",
      "energyDischargedKwh": 0.0,
      "averagePowerKw": 0.0
    }
  ],
  "statusDistribution": [
    {
      "status": "Created",
      "count": 0,
      "percent": 0.0
    }
  ],
  "vesselLeaderboard": [
    {
      "vesselId": "string",
      "contractId": "string | null",
      "totalEnergyDischargedKwh": 0.0,
      "latestPowerKw": 0.0,
      "latestTimestamp": "ISO-8601 datetime | null"
    }
  ],
  "heatmap": [
    {
      "dayLabel": "Mon",
      "bands": [
        { "label": "00-04", "averagePowerKw": 0.0 },
        { "label": "04-08", "averagePowerKw": 0.0 },
        { "label": "08-12", "averagePowerKw": 0.0 },
        { "label": "12-18", "averagePowerKw": 0.0 },
        { "label": "18-24", "averagePowerKw": 0.0 }
      ]
    }
  ],
  "availableEvents": [
    {
      "id": "string",
      "stationId": "string",
      "status": "Active",
      "startTime": "ISO-8601 datetime",
      "endTime": "ISO-8601 datetime",
      "targetEnergyKwh": 0.0,
      "regionLabel": "string"
    }
  ],
  "empty": false,
  "updatedAt": "ISO-8601 datetime"
}
```

Analytics rules:

- Uses measurement telemetry (`energyKwh`, `powerKw`, `timestamp`) as source of truth for historical trends.
- `timeSeries` is rolled up by `grain` (`hour` or `day`) for charting.
- `completionRatePercent = completedContracts / finalizedContracts * 100`, where finalized contracts are `completed|failed|cancelled`.
- `participationRatePercent = uniqueMeasuredVessels / sum(maxParticipants for filtered events) * 100`.
- `heatmap` represents average power by weekday and hour-band (00-04, 04-08, 08-12, 12-18, 18-24).
- Baseline impact metrics (grid load without V2G / avoided load) are not yet available and remain additive future work.

## VO Dashboard

### `GET /api/vo/dashboard`

Vessel-operator dashboard snapshot: current vessel SoC, discharge rate, aggregate metrics, and active contract. Requires authentication.

Request headers:

- `Authorization: Bearer <jwt>`

Success response `200`:

```json
{
  "currentVessel": {
    "id": "string",
    "displayName": "string",
    "socPercent": 0.0,
    "dischargeRateKw": 0.0,
    "capacityKwh": 0.0,
    "maxCapacityKwh": 0.0
  } | null,
  "activeContract": {
    "id": "string",
    "endTime": "ISO-8601 datetime",
    "timeRemainingSeconds": 0,
    "estimatedEarnings": 0.0,
    "energyAmountKwh": 0.0,
    "drEventStatus": "Active",
    "station": {
      "id": "string",
      "displayName": "string",
      "city": "string",
      "provinceOrState": "string",
      "latitude": 0.0,
      "longitude": 0.0
    },
    "committedPowerKw": 0.0,
    "energyDeliveredKwh": 0.0,
    "energyRemainingKwh": 0.0
  } | null,
  "metrics": {
    "contractsCompleted": 0,
    "totalKwhDischarged": 0.0,
    "totalEarnings": 0.0
  },
  "weeklyEarnings": {
    "total": 0.0,
    "dailyEarnings": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "todayIndex": 0
  },
  "updatedAt": "ISO-8601 datetime"
}
```

Semantics:

- `currentVessel` is derived from the authenticated user’s `currentVesselId`; null if not set or vessel not found. `socPercent` is computed as `(capacity / maxCapacity) * 100` when `maxCapacity > 0`. `dischargeRateKw` is the vessel’s `maxDischargeRate`.
- `metrics` are over all of the VO’s vessels (contracts completed, total kWh from completed/active contracts, total earnings from completed contracts).
- `activeContract` is the first contract with status `active` and `endTime` after now; `timeRemainingSeconds` is seconds until that `endTime`. When the linked DR event is in `Active` status, the response is enriched with `drEventStatus`, `station` (location from DREvent → Station), `committedPowerKw`, `energyDeliveredKwh` (sum of measurements), and `energyRemainingKwh`. These fields are absent when no DR event is actively running.
- `weeklyEarnings`: current week (Monday–Sunday UTC). `dailyEarnings` is 7 values for Mon..Sun from completed contracts whose `endTime` falls in that week; `todayIndex` is 0–6 (Mon=0, Sun=6).

Error responses:

- `401`: authentication required
- `404`: user not found
- `500`: dashboard load failure

The VO dashboard UI also shows a **Contracts History** list, sourced from `GET /api/contracts/my-contracts`, displaying only contracts with status `completed`, `failed`, or `cancelled`.

### `GET /api/vo/soc-history`

Weekly state-of-charge (SoC) history for the vessel operator dashboard. Requires authentication and uses the caller’s `currentVesselId` to resolve the vessel.

Request headers:

- `Authorization: Bearer <jwt>`

Success response `200`:

```json
{
  "currentVesselId": "string | null",
  "points": [
    {
      "timestamp": "ISO-8601 datetime",
      "socPercent": 0.0
    }
  ],
  "empty": false,
  "windowStart": "ISO-8601 datetime",
  "windowEnd": "ISO-8601 datetime"
}
```

Semantics:

- The endpoint inspects the authenticated user’s `currentVesselId`. If none is set, it returns an empty `points` array and `currentVesselId: null`.
- The time window is the *previous 7×24 hours* (rolling window), computed from the current UTC time.
- `points` contains measurement-backed SoC telemetry for the current vessel only, sorted by `timestamp` ascending.
- Each `socPercent` value comes from the `currentSOC` field in the measurements table and is clamped to discard clearly invalid values (< 0 or > 200).

Error responses:

- `401`: authentication required
- `404`: user not found
- `500`: SoC history load failure

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
- `energyAmount` may be `0` for a pending contract offer before the vessel operator commits.

### Derived fields

- `totalValue = energyAmount * pricePerKwh` when a committed energy amount is known.

### Status transition rules

- Update accepts only values in `ContractStatus`.
- Cancel endpoint allows only contracts currently in `pending`.
- Complete endpoint allows only contracts currently in `pending` or `active`.
- Accept endpoint requires `committedPowerKw` and accepts optional `operatorNotes`.
- Successful accept stores `committedPowerKw`, `operatorNotes`, `acceptedAt`, and `bookingId`.
- Successful accept derives `energyAmount` from `committedPowerKw * eventDurationHours`.
- Successful accept recalculates `totalValue` from the committed energy contribution.
- Successful accept transitions the contract from `pending` to `active`.
- Successful accept transitions a DR event from `Dispatched` to `Accepted`.

### Filtering/sorting rules

- `GET /api/contracts` supports `status` and `vesselId` filters.
- Results are sorted by `createdAt` descending (newest first).

## DR Event Dispatch Contract

### `POST /api/drevents/{eventId}/dispatch`

Dispatches a `Created` DR event to eligible vessels and issues one pending contract offer
per eligible vessel.

Rules:

- Only power operators can dispatch.
- Dispatch is idempotent for the same `drEventId` + `vesselId` pair.
- Re-dispatching an already `Dispatched` event skips existing offers instead of duplicating them.
- Events outside `Created` or `Dispatched` cannot generate new offers.
- Pending offers are open invitations; they do not pre-allocate the event target energy across vessels.

Success response `200`:

```json
{
  "message": "DR event dispatched successfully",
  "event": {
    "id": "string",
    "status": "Dispatched"
  },
  "eligibleVessels": 0,
  "contractsCreated": 0,
  "contractsSkipped": 0
}
```

Error responses:

- `400`: invalid lifecycle state for dispatch
- `403`: caller is not a power operator
- `404`: DR event not found
- `500`: dispatch failure

### `POST /api/contracts/{contractId}/accept`

Request JSON:

```json
{
  "committedPowerKw": 0.0,
  "operatorNotes": "string (optional)"
}
```

Success response `200`:

```json
{
  "message": "Contract accepted successfully",
  "contract": {
    "id": "string",
    "bookingId": "string | null",
    "vesselId": "string",
    "drEventId": "string",
    "vesselName": "string",
    "energyAmount": 0.0,
    "pricePerKwh": 0.0,
    "totalValue": 0.0,
    "status": "active",
    "committedPowerKw": 0.0,
    "operatorNotes": "string",
    "acceptedAt": "ISO-8601 datetime | null"
  }
}
```

Error responses:

- `400`: missing/invalid `committedPowerKw`
- `403`: caller does not own the vessel on the contract
- `404`: contract, vessel, or DR event not found
- `409`: booking or dock conflict blocks acceptance

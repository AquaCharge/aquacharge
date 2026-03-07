# Data Models

## Users

| Attribute    | Type     | Description                      |
|-------------|----------|----------------------------------|
| id          | String   | User ID                          |
| orgId       | String?  | Organization of user             |
| displayName | String   | Name displayed for user          |
| email       | String   | Email                            |
| passwordHash| String   | Hashed version of password       |
| role        | int      | Role of user (normal, admin)     |
| type        | int      | PSO or VO for normal             |
| active      | bool     | If user is active or not         |
| currentVesselId | String? | Current vessel ID for VO dashboard |
| createdAt   | datetime | Date user created profile        |
| updatedAt   | datetime | Last time user was updated       |

## Stations

| Attribute       | Type   | Description                          |
|----------------|--------|--------------------------------------|
| id             | String | Station ID                           |
| displayName    | String | Name displayed for station           |
| country        | String | Country where station is located     |
| provinceOrState| String | Province/State of station            |
| city           | String | City of station                      |
| longitude      | float  | Longitude of station                 |
| latitude       | float  | Latitude of station                  |
| status         | String | Status of station (open/closed)      |

## Vessels

| Attribute        | Type     | Description                                 |
|-----------------|----------|---------------------------------------------|
| id              | String   | Vessel ID                                   |
| userId          | String   | User ID associated with vessel              |
| displayName     | String   | Name displayed for vessel                   |
| vesselType      | String   | Type of vessel                              |
| chargerType     | String   | Charger type the vessel is compatible with  |
| capacity        | float    | Max battery capacity (kWh)                  |
| maxChargeRate   | float    | Max rate at which battery can be charged    |
| minChargeRate   | float    | Min rate at which battery can be charged    |
| maxDischargeRate| float    | Rate at which battery can be discharged     |
| rangeMeters     | float    | Range of vessel if battery is full          |
| active          | bool     | If vessel is in use or not                  |
| longitude       | float    | Current longitude of vessel                 |
| latitude        | float    | Current latitude of vessel                  |
| createdAt       | datetime | When the vessel was added                   |
| updatedAt       | datetime | When the vessel was last changed            |

## Chargers

| Attribute         | Type   | Description                |
|------------------|--------|----------------------------|
| id               | String | Charger ID                 |
| chargingStationId| String | Station ID of charger      |
| chargerType      | String | Type of charger            |
| maxRate          | float  | Maximum charge rate        |
| status           | String | Current status of charger  |

## Bookings

| Attribute   | Type     | Description                                   |
|------------|----------|-----------------------------------------------|
| id         | String   | Booking ID                                    |
| userId     | String   | User ID for the booking                       |
| vesselId   | String   | Vessel associated with the booking            |
| stationId  | String   | Station where booking is taking place         |
| startTime  | datetime | Planned start time                            |
| endTime    | datetime | Planned end time                              |
| status     | String   | Status of the booking                         |
| chargerId  | String   | Specific charger assigned to this booking     |
| chargerType| String   | Type of charger for compatibility             |
| createdAt  | datetime | Booking creation datetime                     |

## DREvents

| Attribute       | Type     | Description                               |
|----------------|----------|-------------------------------------------|
| id             | String   | DR event ID                               |
| stationId      | String   | Station ID of DR event                    |
| targetEnergyKwh| float    | Target energy to be delivered (kWh)       |
| pricePerKwh    | float    | Price per kWh for the DR event            |
| startTime      | datetime | Datetime of start of DR event             |
| endTime        | datetime | Datetime of end of DR event               |
| maxParticipants| int      | Maximum number of participating vessels   |
| status         | String   | Status of DR event                        |
| details        | JSON?    | Optional additional event metadata        |

## Contracts

| Attribute    | Type     | Description                                    |
|-------------|----------|------------------------------------------------|
| id          | String   | Contract ID                                    |
| bookingId   | String?  | Booking ID associated with contract (optional) |
| vesselId    | String   | Vessel ID party to the contract                |
| drEventId   | String   | DR event this contract belongs to              |
| vesselName  | String   | Display name of the vessel (denormalized)      |
| energyAmount| float    | Energy amount promised by vessel (kWh)         |
| pricePerKwh | float    | Value per kWh                                  |
| totalValue  | float    | Total monetary value of contract               |
| startTime   | datetime | Datetime of start of contract                  |
| endTime     | datetime | Datetime of end of contract                    |
| status      | String   | Status of contract                             |
| terms       | String   | Contract terms text                            |
| createdAt   | datetime | Datetime of creation                           |
| updatedAt   | datetime?| Last time contract was updated                 |
| createdBy   | String   | User ID of PSO who created the contract        |

## Org

| Attribute   | Type   | Description                    |
|------------|--------|--------------------------------|
| id         | String | Organization ID                |
| displayName| String | Displayed name of organization |

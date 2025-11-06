# DynamoDB Integration - Migration Summary

## What Was Changed

### 1. Created DynamoDB Helper Module

**File**: `/backend/db/dynamodb.py`

- Complete DynamoDB client with CRUD operations for all tables
- Singleton instance `db_client` ready to use
- Methods for users, stations, chargers, vessels, and bookings
- Type conversion helpers for DynamoDB Decimal and datetime types
- GSI query support (email-index, orgId-index, city-index, status-index, etc.)

**Key Features**:

- `db_client.get_user_by_email(email)` - Query user by email
- `db_client.create_user(user_dict)` - Create new user
- `db_client.update_user(user_id, user_dict)` - Update user
- Similar methods for stations, chargers, vessels, bookings

### 2. Updated API Endpoints

#### `/backend/api/users.py`

- ✅ Replaced in-memory `users_db` dict with `db_client` calls
- ✅ All endpoints now query/write to DynamoDB
- ✅ GET /api/users - Scans DynamoDB users table
- ✅ GET /api/users/<id> - Gets user by ID from DynamoDB
- ✅ POST /api/users - Creates user in DynamoDB with duplicate email check
- ✅ PUT /api/users/<id> - Updates user in DynamoDB
- ✅ DELETE /api/users/<id> - Deletes user from DynamoDB

#### `/backend/api/auth.py`

- ✅ Replaced all `users_db` references with `db_client` calls
- ✅ POST /api/auth/login - Queries DynamoDB by email
- ✅ POST /api/auth/register - Creates user in DynamoDB
- ✅ POST /api/auth/verify-token - Gets user from DynamoDB
- ✅ POST /api/auth/refresh - Gets user from DynamoDB
- ✅ POST /api/auth/forgot-password - Queries DynamoDB by email
- ✅ POST /api/auth/reset-password - Updates user password in DynamoDB
- ✅ POST /api/auth/change-password - Updates user password in DynamoDB
- ✅ GET /api/auth/me - Gets current user from DynamoDB

### 3. Created Sample Test Data

**Files in** `/backend/test_data/`:

- `users_sample.json` - 3 test users
- `stations_sample.json` - 4 charging stations
- `chargers_sample.json` - 6 chargers
- `vessels_sample.json` - 3 vessels
- `bookings_sample.json` - 4 bookings
- `load_sample_data.py` - Python script to load all data
- `README.md` - Instructions for loading data

## Remaining Work

### API Endpoints to Update (Same Pattern)

1. `/backend/api/stations.py` - Replace in-memory dict with `db_client.create_station()`, `db_client.get_station_by_id()`, etc.
2. `/backend/api/chargers.py` - Replace with `db_client.create_charger()`, `db_client.get_charger_by_station()`, etc.
3. `/backend/api/vessels.py` - Replace with `db_client.create_vessel()`, `db_client.get_vessel_by_user()`, etc.
4. `/backend/api/bookings.py` - Replace with `db_client.create_booking()`, `db_client.get_booking_by_user()`, etc.
5. `/backend/api/contracts.py` - Need to add methods to dynamodb.py first

### Pattern to Follow

**Before (In-Memory)**:

```python
# Old way
stations_db: Dict[str, Station] = {}

@stations_bp.route("", methods=["GET"])
def get_stations():
    return jsonify([s.to_dict() for s in stations_db.values()]), 200

@stations_bp.route("/<station_id>", methods=["GET"])
def get_station(station_id):
    if station_id not in stations_db:
        return jsonify({"error": "Not found"}), 404
    return jsonify(stations_db[station_id].to_dict()), 200
```

**After (DynamoDB)**:

```python
from db.dynamodb import db_client

@stations_bp.route("", methods=["GET"])
def get_stations():
    try:
        stations = db_client.scan_table(db_client.stations_table_name)
        return jsonify([Station.from_dict(s).to_dict() for s in stations]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@stations_bp.route("/<station_id>", methods=["GET"])
def get_station(station_id):
    try:
        station_data = db_client.get_station_by_id(station_id)
        if not station_data:
            return jsonify({"error": "Not found"}), 404
        return jsonify(Station.from_dict(station_data).to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## How to Load Test Data

### Quick Start

```bash
cd backend
python test_data/load_sample_data.py
```

### Test Login

```bash
curl -X POST http://localhost:5050/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password"
  }'
```

## Environment Variables Required

Make sure these are set (in `.env` or environment):

```bash
AWS_REGION=us-west-2
DYNAMODB_USERS_TABLE=aquacharge-users-dev
DYNAMODB_STATIONS_TABLE=aquacharge-stations-dev
DYNAMODB_CHARGERS_TABLE=aquacharge-chargers-dev
DYNAMODB_VESSELS_TABLE=aquacharge-vessels-dev
DYNAMODB_BOOKINGS_TABLE=aquacharge-bookings-dev
DYNAMODB_CONTRACTS_TABLE=aquacharge-contracts-dev
```

## Dependencies

✅ `boto3==1.34.0` already in requirements.txt - no changes needed!

## Next Steps

1. **Load test data**: Run `python test_data/load_sample_data.py`
2. **Update remaining endpoints**: stations, chargers, vessels, bookings (follow same pattern)
3. **Test locally**: Start Flask and test with sample users
4. **Deploy**: Push to EC2 and verify DynamoDB integration works in AWS
5. **Remove sample data code**: Once confirmed working, remove any old in-memory initialization code

## Benefits of This Change

✅ **Persistent Storage**: Data survives container restarts  
✅ **Scalable**: DynamoDB handles high throughput automatically  
✅ **Consistent**: Single source of truth for all services  
✅ **AWS Native**: Integrated with IAM, CloudWatch, and other AWS services  
✅ **GSI Support**: Fast queries by email, orgId, city, status, etc.  
✅ **Type Safe**: Proper handling of DynamoDB Decimal and datetime types

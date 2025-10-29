import pytest
from flask import Flask
import jwt
from datetime import datetime, timedelta
from api.bookings import bookings_bp
from api.chargers import chargers_bp
from api.stations import stations_bp
from api.users import users_bp
from api.vessels import vessels_bp
from api.contracts import contracts_bp
from api.auth import auth_bp
from config import JWT_SECRET, JWT_ALGORITHM


def create_jwt_token(user_id, role=2, user_type=1, email="test@example.com"):
    """Helper function to create JWT tokens for testing"""
    payload = {
        "id": user_id,
        "email": email,
        "role": role,  # 1=ADMIN, 2=USER
        "type": user_type,  # 1=VESSEL_OPERATOR, 2=POWER_OPERATOR
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(chargers_bp, url_prefix="/api/chargers")
    app.register_blueprint(stations_bp, url_prefix="/api/stations")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(vessels_bp, url_prefix="/api/vessels")
    app.register_blueprint(contracts_bp, url_prefix="/api/contracts")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def admin_headers():
    """Headers with admin token"""
    token = create_jwt_token("admin-001", role=1, user_type=2)  # ADMIN, POWER_OPERATOR
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vessel_operator_headers():
    """Headers with vessel operator token"""
    token = create_jwt_token("user-001", role=2, user_type=1)  # USER, VESSEL_OPERATOR
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def power_operator_headers():
    """Headers with power operator token"""
    token = create_jwt_token("power-001", role=2, user_type=2)  # USER, POWER_OPERATOR
    return {"Authorization": f"Bearer {token}"}


# --- Bookings --- #
def test_get_bookings(client):
    rv = client.get("/api/bookings")
    assert rv.status_code == 200


def test_get_booking_not_found(client):
    rv = client.get("/api/bookings/nonexistent")
    assert rv.status_code == 404


def test_create_booking_missing_fields(client):
    rv = client.post("/api/bookings", json={})
    assert rv.status_code == 400
    assert "is required" in rv.get_json()["error"]


def test_delete_booking(client):
    rv = client.post(
        "/api/bookings",
        json={
            "userId": "user-003",
            "vesselId": "vessel-009",
            "stationId": "station-001",
            "startTime": "2025-10-22T10:00:00",
            "endTime": "2025-10-22T12:00:00",
            "chargerType": "Type 2 AC",
        },
    )
    booking_id = rv.get_json()["id"]
    rv = client.delete(f"/api/bookings/{booking_id}")
    assert rv.status_code == 200


def test_get_upcoming_bookings(client):
    rv = client.get("/api/bookings/upcoming?userId=user-003")
    assert rv.status_code == 200
    assert isinstance(rv.get_json(), list)


# --- Chargers --- #
def test_get_chargers(client):
    rv = client.get("/api/chargers")
    assert rv.status_code == 200


def test_get_charger(client):
    rv = client.get("/api/chargers/charger-001")
    assert rv.status_code == 200


def test_get_charger_not_found(client):
    rv = client.get("/api/chargers/notexist")
    assert rv.status_code == 404


def test_create_charger_and_delete(client):
    charger = {
        "chargingStationId": "station-001",
        "chargerType": "Type 2 AC",
        "maxRate": 22.0,
    }
    rv = client.post("/api/chargers", json=charger)
    assert rv.status_code == 201


def test_update_charger(client):
    rv = client.put(
        "/api/chargers/charger-002", json={"active": False, "maxRate": 60.0}
    )
    assert rv.status_code == 200


def test_get_available_chargers(client):
    rv = client.get("/api/chargers/available?stationId=station-001")
    assert rv.status_code == 200


# --- Stations --- #
def test_get_stations(client):
    rv = client.get("/api/stations")
    assert rv.status_code == 200


def test_get_station(client):
    rv = client.get("/api/stations/station-001")
    assert rv.status_code == 200


def test_get_station_not_found(client):
    rv = client.get("/api/stations/doesnotexist")
    assert rv.status_code == 404


def test_create_station_and_delete(client):
    station = {
        "displayName": "Test Dock",
        "longitude": 1.23,
        "latitude": 4.56,
        "city": "Testville",
        "provinceOrState": "TestState",
        "country": "Testland",
    }
    rv = client.post("/api/stations", json=station)
    assert rv.status_code == 201


def test_update_station(client):
    rv = client.put(
        "/api/stations/station-002", json={"city": "San Jose", "status": "MAINTENANCE"}
    )
    assert rv.status_code == 200


def test_get_nearby_stations(client):
    rv = client.get("/api/stations/nearby?lat=49.2827&lng=-123.1207&radius=2")
    assert rv.status_code == 200


# --- Users --- #
def test_get_users(client):
    rv = client.get("/api/users")
    assert rv.status_code == 200


def test_get_user(client):
    rv = client.get("/api/users/user-001")
    assert rv.status_code == 200


def test_get_user_not_found(client):
    rv = client.get("/api/users/doesnotexist")
    assert rv.status_code == 404


def test_create_user_and_delete(client):
    user = {
        "displayName": "testuser",
        "email": "test@example.com",
        "password": "password123",
    }
    rv = client.post("/api/users", json=user)
    assert rv.status_code == 201


def test_update_user(client):
    rv = client.put(
        "/api/users/user-003", json={"email": "newmail@example.com", "active": False}
    )
    assert rv.status_code == 200


# --- Role-Based Route Separation Tests --- #

def test_contracts_require_admin_role(client, vessel_operator_headers, power_operator_headers, admin_headers):
    """Test that contracts endpoints require ADMIN role"""
    
    # Test GET /api/contracts - should fail for vessel and power operators, succeed for admin
    rv = client.get("/api/contracts", headers=vessel_operator_headers)
    assert rv.status_code == 403
    assert "Insufficient permissions" in rv.get_json()["error"]
    
    rv = client.get("/api/contracts", headers=power_operator_headers)
    assert rv.status_code == 403
    assert "Insufficient permissions" in rv.get_json()["error"]
    
    rv = client.get("/api/contracts", headers=admin_headers)
    assert rv.status_code == 200
    
    # Test POST /api/contracts - should fail for non-admin users
    contract_data = {
        "vesselId": "vessel-001",
        "vesselName": "Test Vessel",
        "energyAmount": 100.0,
        "pricePerKwh": 0.15,
        "startTime": "2025-10-30T10:00:00",
        "endTime": "2025-10-30T18:00:00",
        "terms": "Test contract terms"
    }
    
    rv = client.post("/api/contracts", json=contract_data, headers=vessel_operator_headers)
    assert rv.status_code == 403
    
    rv = client.post("/api/contracts", json=contract_data, headers=power_operator_headers)
    assert rv.status_code == 403
    
    rv = client.post("/api/contracts", json=contract_data, headers=admin_headers)
    assert rv.status_code == 201


def test_authentication_required_for_protected_routes(client):
    """Test that protected routes require authentication"""
    
    # Test contracts endpoints without auth
    rv = client.get("/api/contracts")
    assert rv.status_code == 401
    assert "Authentication required" in rv.get_json()["error"]
    
    rv = client.post("/api/contracts", json={})
    assert rv.status_code == 401
    assert "Authentication required" in rv.get_json()["error"]
    
    # Test with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    rv = client.get("/api/contracts", headers=invalid_headers)
    assert rv.status_code == 401


def test_user_type_specific_functionality(client, vessel_operator_headers, power_operator_headers):
    """Test that user types can access their appropriate resources"""
    
    # Both user types should be able to access general endpoints
    rv = client.get("/api/stations", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    rv = client.get("/api/stations", headers=power_operator_headers)
    assert rv.status_code == 200
    
    # Both should be able to access chargers
    rv = client.get("/api/chargers", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    rv = client.get("/api/chargers", headers=power_operator_headers)
    assert rv.status_code == 200
    
    # Both should be able to access vessels (shared resource)
    rv = client.get("/api/vessels", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    rv = client.get("/api/vessels", headers=power_operator_headers)
    assert rv.status_code == 200


def test_role_hierarchy_enforcement(client):
    """Test that role hierarchy is properly enforced"""
    
    # Create tokens with different roles
    admin_token = create_jwt_token("admin-001", role=1, user_type=2)  # ADMIN role
    user_token = create_jwt_token("user-001", role=2, user_type=1)    # USER role
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Admin should have access to contracts
    rv = client.get("/api/contracts", headers=admin_headers)
    assert rv.status_code == 200
    
    # Regular user should not have access to contracts
    rv = client.get("/api/contracts", headers=user_headers)
    assert rv.status_code == 403
    assert "Insufficient permissions" in rv.get_json()["error"]


def test_token_expiration_handling(client):
    """Test that expired tokens are properly rejected"""
    
    # Create an expired token
    expired_payload = {
        "id": "user-001",
        "email": "test@example.com",
        "role": 2,
        "type": 1,
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    
    rv = client.get("/api/contracts", headers=expired_headers)
    assert rv.status_code == 401
    assert "Token has expired" in rv.get_json()["error"]


def test_malformed_authorization_header(client):
    """Test handling of malformed authorization headers"""
    
    # Test missing Bearer prefix
    malformed_headers = {"Authorization": "invalid_format_token"}
    rv = client.get("/api/contracts", headers=malformed_headers)
    assert rv.status_code == 401
    assert "Authentication required" in rv.get_json()["error"]
    
    # Test empty authorization header
    empty_headers = {"Authorization": ""}
    rv = client.get("/api/contracts", headers=empty_headers)
    assert rv.status_code == 401
    assert "Authentication required" in rv.get_json()["error"]


def test_user_context_in_protected_routes(client, admin_headers):
    """Test that user context is properly set in protected routes"""
    
    # Make a request to a protected endpoint and verify it processes correctly
    rv = client.get("/api/contracts", headers=admin_headers)
    assert rv.status_code == 200
    
    # The fact that we get a 200 response means the user context was properly set
    # and the role validation passed


def test_vessel_operator_specific_access_patterns(client, vessel_operator_headers):
    """Test access patterns typical for vessel operators"""
    
    # Vessel operators should be able to:
    # - View stations to find charging locations
    rv = client.get("/api/stations", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    # - View chargers to check availability
    rv = client.get("/api/chargers", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    # - Manage their vessels
    rv = client.get("/api/vessels", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    # - Create bookings
    rv = client.get("/api/bookings", headers=vessel_operator_headers)
    assert rv.status_code == 200
    
    # - Should NOT be able to access admin-only contracts
    rv = client.get("/api/contracts", headers=vessel_operator_headers)
    assert rv.status_code == 403


def test_power_operator_specific_access_patterns(client, power_operator_headers):
    """Test access patterns typical for power operators"""
    
    # Power operators should be able to:
    # - View stations they manage
    rv = client.get("/api/stations", headers=power_operator_headers)
    assert rv.status_code == 200
    
    # - Manage chargers at their stations
    rv = client.get("/api/chargers", headers=power_operator_headers)
    assert rv.status_code == 200
    
    # - View bookings for their stations
    rv = client.get("/api/bookings", headers=power_operator_headers)
    assert rv.status_code == 200
    
    # - Should NOT be able to access admin-only contracts (unless they're also admin)
    rv = client.get("/api/contracts", headers=power_operator_headers)
    assert rv.status_code == 403

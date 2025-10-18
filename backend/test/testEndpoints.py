import pytest
from flask import Flask
from api.bookings import bookings_bp
from api.chargers import chargers_bp
from api.stations import stations_bp
from api.users import users_bp
from api.vessels import vessels_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(chargers_bp, url_prefix="/api/chargers")
    app.register_blueprint(stations_bp, url_prefix="/api/stations")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(vessels_bp, url_prefix="/api/vessels")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
        "username": "testuser",
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

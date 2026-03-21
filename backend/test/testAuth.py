import pytest
import time
from flask import Flask
from api.auth import auth_bp
from api.users import users_bp
import config
from db.dynamoClient import DynamoClient


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_user_credentials(client):
    """Create an isolated auth user for login/token/password tests."""
    timestamp = str(int(time.time() * 1000))
    email = f"auth_test_{timestamp}@example.com"
    password = "BoatAdmin#3232"

    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": f"auth_test_{timestamp}",
            "email": email,
            "password": password,
        },
    )
    assert rv.status_code == 201, f"Auth test user setup failed: {rv.get_json()}"

    return {"email": email, "password": password}


# --- Authentication Tests --- #
def test_login_success(client, auth_user_credentials):
    """Test successful login with valid credentials"""
    rv = client.post(
        "/api/auth/login",
        json=auth_user_credentials,
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == auth_user_credentials["email"]


def test_login_invalid_email(client):
    """Test login with invalid email"""
    rv = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "BoatAdmin#3232"},
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_login_invalid_password(client, auth_user_credentials):
    """Test login with invalid password"""
    rv = client.post(
        "/api/auth/login",
        json={"email": auth_user_credentials["email"], "password": "wrongpassword"},
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_login_missing_fields(client):
    """Test login with missing fields"""
    rv = client.post("/api/auth/login", json={"email": "admin.jason@boats.com"})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_register_success(client):
    """Test successful user registration"""
    import time

    timestamp = str(int(time.time() * 1000))
    test_email = f"test_{timestamp}@example.com"
    test_display_name = f"test_{timestamp}"

    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": test_display_name,
            "email": test_email,
            "password": "BoatAdmin#3232",
        },
    )
    assert rv.status_code == 201, f"Registration failed: {rv.get_json()}"
    data = rv.get_json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == test_email


def test_register_duplicate_email(client):
    """Test registration with duplicate email"""
    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": "testuser456",
            "email": "admin.jason@boats.com",  # Already exists
            "password": "BoatAdmin#3232",
        },
    )
    assert rv.status_code == 409
    data = rv.get_json()
    assert "error" in data


def test_register_weak_password(client):
    """Test registration with weak password"""
    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": "testuser789",
            "email": "weak@example.com",
            "password": "123",  # Too weak
        },
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_register_invalid_email(client):
    """Test registration with invalid email"""
    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": "testuser101",
            "email": "invalid-email",
            "password": "BoatAdmin#3232",
        },
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_verify_token_valid(client, auth_user_credentials):
    """Test token verification with valid token"""
    # First login to get a token
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200, f"Login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Verify the token
    rv = client.post(
        "/api/auth/verify-token", headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200, f"Token verification failed: {rv.get_json()}"
    data = rv.get_json()
    assert data["valid"] is True
    assert "user" in data


def test_verify_token_invalid(client):
    """Test token verification with invalid token"""
    rv = client.post(
        "/api/auth/verify-token", headers={"Authorization": "Bearer invalid-token"}
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_verify_token_missing(client):
    """Test token verification without token"""
    rv = client.post("/api/auth/verify-token")
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_forgot_password(client):
    """Test forgot password request"""
    rv = client.post(
        "/api/auth/forgot-password", json={"email": "admin.jason@boats.com"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "message" in data


def test_forgot_password_invalid_email(client):
    """Test forgot password with invalid email"""
    rv = client.post("/api/auth/forgot-password", json={"email": "invalid-email"})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_get_current_user(client, auth_user_credentials):
    """Test getting current user data"""
    # First login to get a token
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200, f"Login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Get current user
    rv = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200, f"Get current user failed: {rv.get_json()}"
    data = rv.get_json()
    assert data["email"] == auth_user_credentials["email"]


def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication"""
    rv = client.get("/api/auth/me")
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_patch_me_set_current_vessel(client, auth_user_credentials):
    """PATCH /api/auth/me with currentVesselId (owned vessel) returns 200 and updates user."""
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200
    token = login_rv.get_json()["token"]
    user_id = login_rv.get_json()["user"]["id"]

    vessels_client = DynamoClient(
        table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
    )
    vessel_id = "test-vessel-patch-me-" + str(int(time.time() * 1000))
    vessels_client.put_item(
        {
            "id": vessel_id,
            "userId": user_id,
            "displayName": "Test Vessel",
            "vesselType": "ferry",
            "chargerType": "AC",
            "capacity": 50,
            "maxCapacity": 100,
        }
    )
    try:
        rv = client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"currentVesselId": vessel_id},
        )
        assert rv.status_code == 200, rv.get_json()
        data = rv.get_json()
        assert data.get("currentVesselId") == vessel_id

        get_rv = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert get_rv.status_code == 200
        assert get_rv.get_json().get("currentVesselId") == vessel_id
    finally:
        try:
            vessels_client.delete_item(key={"id": vessel_id})
        except Exception:
            pass


def test_patch_me_clear_current_vessel(client, auth_user_credentials):
    """PATCH /api/auth/me with currentVesselId null clears and returns 200."""
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200
    token = login_rv.get_json()["token"]
    user_id = login_rv.get_json()["user"]["id"]

    vessels_client = DynamoClient(
        table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
    )
    vessel_id = "test-vessel-clear-" + str(int(time.time() * 1000))
    vessels_client.put_item(
        {
            "id": vessel_id,
            "userId": user_id,
            "displayName": "Test Vessel",
            "vesselType": "ferry",
            "chargerType": "AC",
            "capacity": 50,
            "maxCapacity": 100,
        }
    )
    try:
        client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"currentVesselId": vessel_id},
        )
        rv = client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"currentVesselId": None},
        )
        assert rv.status_code == 200, rv.get_json()
        assert rv.get_json().get("currentVesselId") is None
    finally:
        try:
            vessels_client.delete_item(key={"id": vessel_id})
        except Exception:
            pass


def test_patch_me_forbidden_when_vessel_not_owned(client, auth_user_credentials):
    """PATCH /api/auth/me with a vessel id not owned by user returns 403."""
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200
    token = login_rv.get_json()["token"]

    rv = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"currentVesselId": "some-other-users-vessel-id"},
    )
    assert rv.status_code == 403
    data = rv.get_json()
    assert "error" in data


def test_refresh_token(client, auth_user_credentials):
    """Test token refresh"""
    # First login to get a token
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200, f"Login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Refresh the token
    rv = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200, f"Token refresh failed: {rv.get_json()}"
    data = rv.get_json()
    assert "token" in data
    assert "expires_in" in data


def test_logout(client):
    """Test logout endpoint"""
    rv = client.post("/api/auth/logout")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "message" in data


@pytest.mark.order_last
def test_change_password(client, auth_user_credentials):
    """Test password change"""
    new_password = "newpassword123"

    # First login to get a token
    login_rv = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_rv.status_code == 200, f"Initial login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Change password
    rv = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": auth_user_credentials["password"],
            "new_password": new_password,
        },
    )
    assert rv.status_code == 200, f"Password change failed: {rv.get_json()}"

    login_old = client.post("/api/auth/login", json=auth_user_credentials)
    assert login_old.status_code == 401

    login_new = client.post(
        "/api/auth/login",
        json={"email": auth_user_credentials["email"], "password": new_password},
    )
    assert (
        login_new.status_code == 200
    ), f"Login with new password failed: {login_new.get_json()}"

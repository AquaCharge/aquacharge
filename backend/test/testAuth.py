import pytest
from flask import Flask
from api.auth import auth_bp
from api.users import users_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Authentication Tests --- #
def test_login_success(client):
    """Test successful login with valid credentials"""
    rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == "admin@aquacharge.com"


def test_login_invalid_email(client):
    """Test login with invalid email"""
    rv = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_login_invalid_password(client):
    """Test login with invalid password"""
    rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "wrongpassword"},
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_login_missing_fields(client):
    """Test login with missing fields"""
    rv = client.post("/api/auth/login", json={"email": "admin@aquacharge.com"})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_register_success(client):
    """Test successful user registration"""
    rv = client.post(
        "/api/auth/register",
        json={
            "username": "testuser123",
            "email": "testuser@example.com",
            "password": "password123",
        },
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == "testuser@example.com"


def test_register_duplicate_email(client):
    """Test registration with duplicate email"""
    rv = client.post(
        "/api/auth/register",
        json={
            "username": "testuser456",
            "email": "admin@aquacharge.com",  # Already exists
            "password": "password123",
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
            "username": "testuser789",
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
            "username": "testuser101",
            "email": "invalid-email",
            "password": "password123",
        },
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_verify_token_valid(client):
    """Test token verification with valid token"""
    # First login to get a token
    login_rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    token = login_rv.get_json()["token"]

    # Verify the token
    rv = client.post(
        "/api/auth/verify-token", headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
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
        "/api/auth/forgot-password", json={"email": "admin@aquacharge.com"}
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


def test_get_current_user(client):
    """Test getting current user data"""
    # First login to get a token
    login_rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    token = login_rv.get_json()["token"]

    # Get current user
    rv = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["email"] == "admin@aquacharge.com"


def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication"""
    rv = client.get("/api/auth/me")
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_refresh_token(client):
    """Test token refresh"""
    # First login to get a token
    login_rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    token = login_rv.get_json()["token"]

    # Refresh the token
    rv = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "expires_in" in data


def test_logout(client):
    """Test logout endpoint"""
    rv = client.post("/api/auth/logout")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "message" in data


def test_change_password(client):
    """Test password change"""
    # First login to get a token
    login_rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    token = login_rv.get_json()["token"]

    # Change password
    rv = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "admin123", "new_password": "newpassword123"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "message" in data

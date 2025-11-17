import pytest
from flask import Flask
from api.auth import auth_bp
from api.users import users_bp
from db.dynamoClient import DynamoClient
from boto3.dynamodb.conditions import Key

# Track created test users for cleanup
created_test_emails = []


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def cleanup_users():
    """Automatically clean up test users after each test"""
    yield  # Run the test first
    
    # Cleanup: Delete all test users created during the test
    # BUT never delete the admin user or other pre-existing users
    if created_test_emails:
        dynamo_client = DynamoClient(
            table_name="aquacharge-users-dev", region_name="us-east-1"
        )
        for email in created_test_emails:
            # Skip admin and any other system users
            if email in ["admin@aquacharge.com"]:
                continue
                
            try:
                users = dynamo_client.query_gsi(
                    index_name="email-index",
                    key_condition_expression=Key("email").eq(email),
                )
                if users:
                    dynamo_client.delete_item(key={"id": users[0]["id"]})
                    print(f"Cleaned up test user: {email}")
            except Exception as e:
                print(f"Cleanup failed for {email}: {e}")
        created_test_emails.clear()


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
    import time
    
    # Use timestamp to ensure uniqueness and make cleanup easier
    timestamp = str(int(time.time() * 1000))  # milliseconds for uniqueness
    test_email = f"test_{timestamp}@example.com"
    test_display_name = f"test_{timestamp}"
    
    # Clean up any existing test user first (from failed previous runs)
    dynamo_client = DynamoClient(
        table_name="aquacharge-users-dev", region_name="us-east-1"
    )
    try:
        # Check by email using GSI
        existing = dynamo_client.query_gsi(
            index_name="email-index",
            key_condition_expression=Key("email").eq(test_email),
        )
        if existing:
            for user in existing:
                dynamo_client.delete_item(key={"id": user["id"]})
                print(f"Pre-test cleanup: removed existing user with email {test_email}")
    except Exception as e:
        print(f"Pre-test cleanup failed: {e}")
    
    # Track this email for post-test cleanup
    created_test_emails.append(test_email)

    rv = client.post(
        "/api/auth/register",
        json={
            "displayName": test_display_name,  # Use the variable, not the hardcoded string!
            "email": test_email,
            "password": "password123",
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
    assert login_rv.status_code == 200, f"Login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Get current user
    rv = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200, f"Get current user failed: {rv.get_json()}"
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
def test_change_password(client):
    """Test password change"""
    # First login to get a token
    login_rv = client.post(
        "/api/auth/login",
        json={"email": "admin@aquacharge.com", "password": "admin123"},
    )
    assert login_rv.status_code == 200, f"Initial login failed: {login_rv.get_json()}"
    token = login_rv.get_json()["token"]

    # Change password
    rv = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "admin123", "new_password": "newpassword123"},
    )
    
    # Store the result but don't assert yet - we need to restore password first
    change_success = rv.status_code == 200
    change_data = rv.get_json()

    # ALWAYS restore original password, even if the test fails
    try:
        # Login with new password
        login_rv2 = client.post(
            "/api/auth/login",
            json={"email": "admin@aquacharge.com", "password": "newpassword123"},
        )
        if login_rv2.status_code == 200:
            token2 = login_rv2.get_json()["token"]

            # Change back to original
            client.post(
                "/api/auth/change-password",
                headers={"Authorization": f"Bearer {token2}"},
                json={"current_password": "newpassword123", "new_password": "admin123"},
            )
            print("Successfully restored admin password to original")
    except Exception as e:
        print(f"WARNING: Failed to restore admin password: {e}")
    
    # Now assert the results
    assert change_success, f"Password change failed: {change_data}"
    assert "message" in change_data

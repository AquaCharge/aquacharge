"""Tests for GET /api/vo/dashboard."""

import time
import pytest
from flask import Flask

from api.auth import auth_bp
from api.vo_dashboard import vo_dashboard_bp

created_test_emails = []


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(vo_dashboard_bp, url_prefix="/api/vo")
    with app.test_client() as c:
        yield c


@pytest.fixture
def vo_user_credentials(client):
    """Create a VO user and return login credentials."""
    ts = str(int(time.time() * 1000))
    email = f"vo_dash_{ts}@example.com"
    password = "VoDash#1234"
    created_test_emails.append(email)
    rv = client.post(
        "/api/auth/register",
        json={"displayName": f"vo_dash_{ts}", "email": email, "password": password},
    )
    assert rv.status_code == 201, rv.get_json()
    return {"email": email, "password": password}


def test_vo_dashboard_requires_auth(client):
    """GET /api/vo/dashboard without token returns 401."""
    rv = client.get("/api/vo/dashboard")
    assert rv.status_code == 401
    data = rv.get_json()
    assert "error" in data


def test_vo_dashboard_returns_structure(client, vo_user_credentials):
    """GET /api/vo/dashboard with valid token returns 200 and expected shape."""
    login_rv = client.post("/api/auth/login", json=vo_user_credentials)
    assert login_rv.status_code == 200
    token = login_rv.get_json()["token"]

    rv = client.get("/api/vo/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200, rv.get_json()
    data = rv.get_json()

    assert "currentVessel" in data
    assert "activeContract" in data
    assert "metrics" in data
    assert "updatedAt" in data
    assert data["currentVessel"] is None
    assert data["metrics"]["contractsCompleted"] >= 0
    assert "totalKwhDischarged" in data["metrics"]
    assert "totalEarnings" in data["metrics"]

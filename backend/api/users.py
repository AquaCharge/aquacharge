from flask import Blueprint, jsonify, request
from backend.models.user import User, UserRole
from datetime import datetime
from typing import Dict
import hashlib

users_bp = Blueprint("users", __name__)

# In-memory storage (replace with actual database)
users_db: Dict[str, User] = {}


# Initialize with sample data
def init_sample_users():
    if not users_db:  # Only initialize if empty
        sample_users = [
            User(
                id="user-001",
                username="admin_user",
                email="admin@aquacharge.com",
                passwordHash=hashlib.sha256("admin123".encode()).hexdigest(),
                role=UserRole.ADMIN.value,
                active=True,
                orgId="org-001",
                createdAt=datetime(2024, 1, 15, 10, 30, 0),
                updatedAt=datetime(2024, 2, 1, 14, 20, 0),
            ),
            User(
                id="user-002",
                username="marina_operator",
                email="operator@blueharbor.com",
                passwordHash=hashlib.sha256("operator456".encode()).hexdigest(),
                role=UserRole.OPERATOR.value,
                active=True,
                orgId="org-002",
                createdAt=datetime(2024, 2, 10, 9, 15, 0),
                updatedAt=None,
            ),
            User(
                id="user-003",
                username="boat_owner",
                email="captain@oceanbreezes.com",
                passwordHash=hashlib.sha256("user789".encode()).hexdigest(),
                role=UserRole.USER.value,
                active=True,
                orgId=None,
                createdAt=datetime(2024, 3, 5, 16, 45, 0),
                updatedAt=datetime(2024, 3, 20, 11, 30, 0),
            ),
            User(
                id="user-004",
                username="yacht_club",
                email="management@royalyacht.com",
                passwordHash=hashlib.sha256("yacht2024".encode()).hexdigest(),
                role=UserRole.USER.value,
                active=True,
                orgId="org-003",
                createdAt=datetime(2024, 1, 20, 13, 10, 0),
                updatedAt=None,
            ),
            User(
                id="user-005",
                username="fleet_manager",
                email="fleet@commercialmarine.com",
                passwordHash=hashlib.sha256("fleet555".encode()).hexdigest(),
                role=UserRole.USER.value,
                active=False,
                orgId="org-004",
                createdAt=datetime(2024, 4, 1, 8, 0, 0),
                updatedAt=datetime(2024, 4, 15, 17, 25, 0),
            ),
        ]

        for user in sample_users:
            users_db[user.id] = user


# Initialize sample data when module is imported
init_sample_users()


@users_bp.route("", methods=["GET"])
def get_users():
    """Get all users"""
    users_list = [user.to_public_dict() for user in users_db.values()]
    return jsonify(users_list), 200


@users_bp.route("/<user_id>", methods=["GET"])
def get_user(user_id: str):
    """Get a specific user by ID"""
    if user_id not in users_db:
        return jsonify({"error": "User not found"}), 404

    return jsonify(users_db[user_id].to_public_dict()), 200


@users_bp.route("", methods=["POST"])
def create_user():
    """Create a new user"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["username", "email", "password"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Create user instance
    user = User(
        username=data["username"],
        email=data["email"],
        passwordHash=hashlib.sha256(data["password"].encode()).hexdigest(),
        role=(
            UserRole[data.get("role", "USER")].value
            if "role" in data
            else UserRole.USER.value
        ),
        orgId=data.get("orgId"),
    )

    # Validate user data
    try:
        user.validate()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Store user
    users_db[user.id] = user

    return jsonify(user.to_public_dict()), 201


@users_bp.route("/<user_id>", methods=["PUT"])
def update_user(user_id: str):
    """Update an existing user"""
    if user_id not in users_db:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    user = users_db[user_id]

    # Update allowed fields
    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    if "role" in data:
        user.role = UserRole[data["role"]].value
    if "active" in data:
        user.active = data["active"]
    if "orgId" in data:
        user.orgId = data["orgId"]

    user.updatedAt = datetime.now()

    # Validate updated user
    try:
        user.validate()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(user.to_public_dict()), 200


@users_bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id: str):
    """Delete a user"""
    if user_id not in users_db:
        return jsonify({"error": "User not found"}), 404

    del users_db[user_id]
    return jsonify({"message": "User deleted successfully"}), 200

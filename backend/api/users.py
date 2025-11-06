from flask import Blueprint, jsonify, request
from models.user import User, UserRole, UserType
from datetime import datetime
import hashlib

# Import DynamoDB client
from db.dynamodb import db_client

users_bp = Blueprint("users", __name__)


@users_bp.route("", methods=["GET"])
def get_users():
    """Get all users"""
    try:
        users = db_client.scan_table(db_client.users_table_name)
        users_list = [User.from_dict(user).to_public_dict() for user in users]
        return jsonify(users_list), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch users", "details": str(e)}), 500


@users_bp.route("/<user_id>", methods=["GET"])
def get_user(user_id: str):
    """Get a specific user by ID"""
    try:
        user_data = db_client.get_user_by_id(user_id)
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        user = User.from_dict(user_data)
        return jsonify(user.to_public_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch user", "details": str(e)}), 500


@users_bp.route("", methods=["POST"])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["displayName", "email", "password"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Check if email already exists
        existing_user = db_client.get_user_by_email(data["email"])
        if existing_user:
            return jsonify({"error": "Email already exists"}), 409

        # Create user instance
        user = User(
            displayName=data["displayName"],
            email=data["email"],
            passwordHash=hashlib.sha256(data["password"].encode()).hexdigest(),
            role=(
                UserRole[data.get("role", "USER")].value
                if "role" in data
                else UserRole.USER.value
            ),
            type=(
                UserType[data.get("type", "VESSEL_OPERATOR")].value
                if "type" in data
                else UserType.VESSEL_OPERATOR.value
            ),
            orgId=data.get("orgId"),
        )

        # Validate user data
        try:
            user.validate()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Store user in DynamoDB
        db_client.create_user(user.to_dict())

        return jsonify(user.to_public_dict()), 201
    except Exception as e:
        return jsonify({"error": "Failed to create user", "details": str(e)}), 500


@users_bp.route("/<user_id>", methods=["PUT"])
def update_user(user_id: str):
    """Update an existing user"""
    try:
        user_data = db_client.get_user_by_id(user_id)
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        user = User.from_dict(user_data)

        # Update allowed fields
        if "displayName" in data:
            user.displayName = data["displayName"]
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

        # Update in DynamoDB
        db_client.update_user(user_id, user.to_dict())

        return jsonify(user.to_public_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to update user", "details": str(e)}), 500


@users_bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id: str):
    """Delete a user"""
    try:
        user_data = db_client.get_user_by_id(user_id)
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        db_client.delete_user(user_id)
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete user", "details": str(e)}), 500

from flask import Blueprint, jsonify, request
from models.user import User, UserRole, UserType
import hashlib
from db.dynamoClient import DynamoClient


dynamoDB_client = DynamoClient(
    table_name="aquacharge-users-dev", region_name="us-east-1"
)

users_bp = Blueprint("users", __name__)


@users_bp.route("", methods=["GET"])
def get_users():
    """Get all users"""
    users = dynamoDB_client.scan_items()
    return jsonify(users), 200


@users_bp.route("/<user_id>", methods=["GET"])
def get_user(user_id: str):
    """Get a specific user by ID"""

    user = dynamoDB_client.get_item({"id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200


@users_bp.route("", methods=["POST"])
def create_user():
    """Create a new user"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["displayName", "email", "password"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

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

    # Store user - remove None values for GSI compatibility
    user_dict = user.to_dict()
    user_dict = {k: v for k, v in user_dict.items() if v is not None}

    dynamoDB_client.put_item(user_dict)

    return jsonify(user.to_public_dict()), 201


@users_bp.route("/<user_id>", methods=["PUT"])
def update_user(user_id: str):
    """Update an existing user"""
    # Get user from database
    user_data = dynamoDB_client.get_item(key={"id": user_id})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    # Create current user object
    current_user = User(**user_data)

    # Build update dictionary with only provided fields
    update_data = {}
    if "displayName" in data:
        update_data["displayName"] = data["displayName"]
        current_user.displayName = data["displayName"]
    if "email" in data:
        update_data["email"] = data["email"]
        current_user.email = data["email"]
    if "role" in data:
        update_data["role"] = UserRole[data["role"]].value
        current_user.role = UserRole[data["role"]].value
    if "active" in data:
        update_data["active"] = data["active"]
        current_user.active = data["active"]
    if "orgId" in data:
        update_data["orgId"] = data["orgId"]
        current_user.orgId = data["orgId"]

    # Validate the updated user before saving
    try:
        current_user.validate()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Update the item in DynamoDB
    updated_user_dict = dynamoDB_client.update_item(
        key={"id": user_id}, update_data=update_data
    )

    updated_user = User(**updated_user_dict)
    return jsonify(updated_user.to_public_dict()), 200


@users_bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id: str):
    """Delete a user"""
    user = dynamoDB_client.get_item(key={"id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    dynamoDB_client.delete_item(key={"id": user_id})
    return jsonify({"message": "User deleted successfully"}), 200

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import hashlib
import jwt
import re
from boto3.dynamodb.conditions import Attr, Key
from flask import current_app

from db.dynamoClient import DynamoClient
from models.user import User, UserRole, UserType


def convert_decimals(obj):
    """Convert Decimal objects for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def prepare_user_data_from_dynamo(data: dict) -> dict:
    """Convert DynamoDB types into values expected by the User model."""
    data = convert_decimals(data)

    if "createdAt" in data and isinstance(data["createdAt"], str):
        data["createdAt"] = datetime.fromisoformat(data["createdAt"])
    if "updatedAt" in data and isinstance(data["updatedAt"], str):
        data["updatedAt"] = datetime.fromisoformat(data["updatedAt"])

    return data


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True


class AuthService:
    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.dynamo_client = dynamo_client or DynamoClient(
            table_name="aquacharge-users-dev", region_name="us-east-1"
        )

    def _get_jwt_config(self) -> Tuple[str, str, timedelta]:
        try:
            jwt_secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
            jwt_algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
            jwt_expiry = current_app.config.get(
                "JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=24)
            )
        except RuntimeError:
            jwt_secret = "dev-jwt-secret-key"
            jwt_algorithm = "HS256"
            jwt_expiry = timedelta(hours=24)
        return jwt_secret, jwt_algorithm, jwt_expiry

    def _generate_jwt_token(self, user: User) -> str:
        jwt_secret, jwt_algorithm, jwt_expiry = self._get_jwt_config()
        payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "type": user.type,
            "exp": datetime.utcnow() + jwt_expiry,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

    def _decode_jwt_token(self, token: str) -> Dict[str, Any]:
        jwt_secret, jwt_algorithm, _ = self._get_jwt_config()
        try:
            return jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise ValueError("Invalid token") from exc

    def _find_users_by_email(self, email: str) -> list:
        """Lookup by GSI first, with scan fallback for environments without index consistency."""
        try:
            users = self.dynamo_client.query_gsi(
                index_name="email-index", key_condition_expression=Key("email").eq(email)
            )
            if users:
                return users
        except Exception:
            # Fall through to scan fallback below.
            pass

        return self.dynamo_client.scan_items(filter_expression=Attr("email").eq(email))

    def login(self, data: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        try:
            if not data or "email" not in data or "password" not in data:
                return {"error": "Email and password are required"}, 400

            email = data["email"].lower().strip()
            password = data["password"]

            users = self._find_users_by_email(email)
            if not users:
                return {"error": "Invalid credentials"}, 401

            user_data = prepare_user_data_from_dynamo(users[0])
            user = User(**user_data)

            if not user.active:
                return {"error": "Account is deactivated"}, 401
            if not verify_password(password, user.passwordHash):
                return {"error": "Invalid credentials"}, 401

            token = self._generate_jwt_token(user)
            self.dynamo_client.update_item(
                key={"id": user.id}, update_data={"updatedAt": datetime.now().isoformat()}
            )

            response_user = user.to_public_dict()
            response_user["role_name"] = UserRole(user.role).name
            response_user["type_name"] = UserType(user.type).name

            return {
                "token": token,
                "user": convert_decimals(response_user),
                "expires_in": 24 * 3600,
            }, 200
        except Exception as exc:
            return {"error": "Login failed", "details": str(exc)}, 500

    def register(self, data: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        try:
            if not data:
                return {"error": "Request body is required"}, 400

            required_fields = ["displayName", "email", "password"]
            for field in required_fields:
                if field not in data or not data[field]:
                    return {"error": f"{field} is required"}, 400

            display_name = data["displayName"].strip()
            email = data["email"].lower().strip()
            password = data["password"]

            if not validate_email(email):
                return {"error": "Invalid email format"}, 400
            if not validate_password(password):
                return {
                    "error": "Password must be at least 8 characters and contain letters and numbers"
                }, 400

            existing_users = self._find_users_by_email(email)
            if existing_users:
                return {"error": "Email already registered"}, 409

            user = User(
                displayName=display_name,
                email=email,
                passwordHash=hash_password(password),
                role=UserRole.USER.value,
                type=UserType.VESSEL_OPERATOR.value,
                active=True,
                orgId=data.get("orgId"),
            )
            user.validate()

            user_dict = user.to_dict()
            user_dict = {k: v for k, v in user_dict.items() if v is not None}
            self.dynamo_client.put_item(user_dict)

            token = self._generate_jwt_token(user)
            response_user = user.to_public_dict()
            response_user["role_name"] = UserRole(user.role).name
            response_user["type_name"] = UserType(user.type).name

            return {
                "token": token,
                "user": response_user,
                "message": "Registration successful",
            }, 201
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception as exc:
            return {"error": "Registration failed", "details": str(exc)}, 500

    def verifyJWT(self, auth_header: Optional[str]) -> Tuple[Dict[str, Any], int]:
        try:
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"error": "No valid token provided"}, 401

            token = auth_header.split(" ")[1]
            try:
                payload = self._decode_jwt_token(token)
            except ValueError as exc:
                return {"error": str(exc)}, 401

            user_id = payload.get("user_id")
            user_data = self.dynamo_client.get_item(key={"id": user_id})
            if not user_data:
                return {"error": "User not found"}, 404

            prepared_data = prepare_user_data_from_dynamo(user_data)
            user = User(**prepared_data)
            if not user.active:
                return {"error": "Account is deactivated"}, 401

            response_user = user.to_public_dict()
            response_user["role_name"] = UserRole(user.role).name
            response_user["type_name"] = UserType(user.type).name

            return {"user": convert_decimals(response_user), "valid": True}, 200
        except Exception as exc:
            return {"error": "Token verification failed", "details": str(exc)}, 500

    def logout(self) -> Tuple[Dict[str, Any], int]:
        return {"message": "Logged out successfully"}, 200

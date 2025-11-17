from flask import Blueprint, jsonify, request, current_app
from models.user import User, UserRole, UserType
from datetime import datetime, timedelta
from typing import Dict, Any
from db.dynamoClient import DynamoClient
from boto3.dynamodb.conditions import Attr, Key
from decimal import Decimal
import hashlib
import jwt
import secrets
import re

auth_bp = Blueprint("auth", __name__)

# Initialize DynamoDB client
dynamoDB_client = DynamoClient(table_name="aquacharge-users-dev", region_name="us-east-1")

# In-memory storage for password reset tokens (replace with database in production)
password_reset_tokens: Dict[str, Dict[str, Any]] = {}


# Helper functions
def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def prepare_user_data_from_dynamo(data: dict) -> dict:
    """Prepare user data from DynamoDB for User model"""
    # Convert Decimals
    data = convert_decimals(data)
    
    # Convert ISO datetime strings to datetime objects
    if 'createdAt' in data and isinstance(data['createdAt'], str):
        data['createdAt'] = datetime.fromisoformat(data['createdAt'])
    if 'updatedAt' in data and isinstance(data['updatedAt'], str):
        data['updatedAt'] = datetime.fromisoformat(data['updatedAt'])
    
    return data


def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == hashed


def generate_jwt_token(user: User) -> str:
    """Generate a JWT token for a user"""
    # Get config from current app or use defaults
    try:
        jwt_secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
        jwt_algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
        jwt_expiry = current_app.config.get(
            "JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=24)
        )
    except RuntimeError:
        # Fallback for testing without app context
        jwt_secret = "dev-jwt-secret-key"
        jwt_algorithm = "HS256"
        jwt_expiry = timedelta(hours=24)

    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "type": user.type,
        "exp": datetime.utcnow() + jwt_expiry,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        jwt_secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
        jwt_algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
    except RuntimeError:
        # Fallback for testing without app context
        jwt_secret = "dev-jwt-secret-key"
        jwt_algorithm = "HS256"

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """Validate password strength"""
    # At least 8 characters, contains letters and numbers
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True


# Routes
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data or "email" not in data or "password" not in data:
            return jsonify({"error": "Email and password are required"}), 400

        email = data["email"].lower().strip()
        password = data["password"]

        # Find user by email using GSI
        users = dynamoDB_client.query_gsi(
            index_name="email-index",
            key_condition_expression=Key('email').eq(email)
        )
        
        if not users:
            return jsonify({"error": "Invalid credentials"}), 401

        # Prepare user data from DynamoDB
        user_data = prepare_user_data_from_dynamo(users[0])
        user = User(**user_data)

        # Check if user is active
        if not user.active:
            return jsonify({"error": "Account is deactivated"}), 401

        # Verify password
        print(hash_password(password))
        print(verify_password(password, user.passwordHash))
        if not verify_password(password, user.passwordHash):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate JWT token
        token = generate_jwt_token(user)

        # Update last login time
        update_data = {'updatedAt': datetime.now().isoformat()}
        dynamoDB_client.update_item(key={'id': user.id}, update_data=update_data)

        # Return user data (without password) and token
        user_data = user.to_public_dict()
        
        # Add human-readable role and type names
        # user.role and user.type are integers, so we get the enum by value
        user_data["role_name"] = UserRole(user.role).name
        user_data["type_name"] = UserType(user.type).name
        
        # Convert any Decimal objects to float for JSON serialization
        user_data = convert_decimals(user_data)

        return (
            jsonify(
                {
                    "token": token,
                    "user": user_data,
                    "expires_in": 24 * 3600,  # 24 hours in seconds
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["displayName", "email", "password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        displayName = data["displayName"].strip()
        email = data["email"].lower().strip()
        password = data["password"]

        # Validate email format
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        # Validate password strength
        if not validate_password(password):
            return (
                jsonify(
                    {
                        "error": "Password must be at least 8 characters and contain letters and numbers"
                    }
                ),
                400,
            )

        # Check if email already exists using GSI for consistency
        existing_users = dynamoDB_client.query_gsi(
            index_name="email-index",
            key_condition_expression=Key('email').eq(email)
        )
        if existing_users:
            return jsonify({"error": "Email already registered"}), 409

        # Display names can be duplicated - no uniqueness check needed

        # Create new user
        user = User(
            displayName=displayName,
            email=email,
            passwordHash=hash_password(password),
            role=UserRole.USER.value,
            type=UserType.VESSEL_OPERATOR.value,
            active=True,
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

        # Generate JWT token for auto-login
        token = generate_jwt_token(user)

        # Return user data (without password) and token
        user_data = user.to_public_dict()
        user_data["role_name"] = UserRole(user.role).name
        user_data["type_name"] = UserType(user.type).name

        return (
            jsonify(
                {
                    "token": token,
                    "user": user_data,
                    "message": "Registration successful",
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": "Registration failed", "details": str(e)}), 500


@auth_bp.route("/verify-token", methods=["POST"])
def verify_token():
    """Verify JWT token and return user data"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "No valid token provided"}), 401

        token = auth_header.split(" ")[1]

        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        # Get user from database
        user_id = payload.get("user_id")
        user_data = dynamoDB_client.get_item(key={'id': user_id})
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Convert Decimals before creating User object
        user_data = prepare_user_data_from_dynamo(user_data)
        user = User(**user_data)

        # Check if user is still active
        if not user.active:
            return jsonify({"error": "Account is deactivated"}), 401

        # Return user data
        user_data = user.to_public_dict()
        user_data["role_name"] = UserRole(user.role).name
        user_data["type_name"] = UserType(user.type).name
        
        # Ensure all Decimals are converted
        user_data = convert_decimals(user_data)

        return jsonify({"user": user_data, "valid": True}), 200

    except Exception as e:
        return jsonify({"error": "Token verification failed", "details": str(e)}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh JWT token"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "No valid token provided"}), 401

        token = auth_header.split(" ")[1]

        # Decode token (even if expired)
        try:
            jwt_secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
            jwt_algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
        except RuntimeError:
            jwt_secret = "dev-jwt-secret-key"
            jwt_algorithm = "HS256"

        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=[jwt_algorithm],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # Get user from database
        user_id = payload.get("user_id")
        user_data = dynamoDB_client.get_item(key={'id': user_id})
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Convert Decimals before creating User object
        user_data = prepare_user_data_from_dynamo(user_data)
        user = User(**user_data)

        # Check if user is still active
        if not user.active:
            return jsonify({"error": "Account is deactivated"}), 401

        # Generate new token
        new_token = generate_jwt_token(user)

        return (
            jsonify(
                {"token": new_token, "expires_in": 24 * 3600}  # 24 hours in seconds
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Token refresh failed", "details": str(e)}), 500


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Send password reset token"""
    try:
        data = request.get_json()

        if not data or "email" not in data:
            return jsonify({"error": "Email is required"}), 400

        email = data["email"].lower().strip()

        # Validate email format
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        # Find user by email
        users = dynamoDB_client.scan_items(
            filter_expression=Attr('email').eq(email)
        )

        # Always return success to prevent email enumeration
        # But only actually process if user exists
        if users and len(users) > 0:
            user_data = users[0]
            user = User(**user_data)
            
            if user.active:
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)

                # Store reset token with expiry
                password_reset_tokens[reset_token] = {
                    "user_id": user.id,
                    "email": user.email,
                    "expires_at": datetime.now() + timedelta(hours=2),  # 2 hours
                    "used": False,
                }

                # TODO: Send email with reset link
                reset_link = f"https://aquacharge.com/reset-password?token={reset_token}"
                print(f"Password reset link for {email}: {reset_link}")

        return (
            jsonify(
                {
                    "message": "If an account with that email exists, a password reset link has been sent."
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify({"error": "Password reset request failed", "details": str(e)}),
            500,
        )


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Reset password using reset token"""
    try:
        data = request.get_json()

        required_fields = ["token", "new_password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        token = data["token"]
        new_password = data["new_password"]

        # Validate password strength
        if not validate_password(new_password):
            return (
                jsonify(
                    {
                        "error": "Password must be at least 8 characters and contain letters and numbers"
                    }
                ),
                400,
            )

        # Check if token exists and is valid
        if token not in password_reset_tokens:
            return jsonify({"error": "Invalid or expired reset token"}), 400

        token_data = password_reset_tokens[token]

        # Check if token is expired
        if datetime.now() > token_data["expires_at"]:
            del password_reset_tokens[token]
            return jsonify({"error": "Reset token has expired"}), 400

        # Check if token was already used
        if token_data["used"]:
            return jsonify({"error": "Reset token has already been used"}), 400

        # Get user
        user_id = token_data["user_id"]
        user_data = dynamoDB_client.get_item(key={'id': user_id})
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Update password
        update_data = {
            'passwordHash': hash_password(new_password),
            'updatedAt': datetime.now().isoformat()
        }
        dynamoDB_client.update_item(key={'id': user_id}, update_data=update_data)

        # Mark token as used
        token_data["used"] = True

        return jsonify({"message": "Password has been reset successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Password reset failed", "details": str(e)}), 500


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change password for authenticated user"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(" ")[1]

        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        data = request.get_json()

        required_fields = ["current_password", "new_password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        current_password = data["current_password"]
        new_password = data["new_password"]

        # Validate new password strength
        if not validate_password(new_password):
            return (
                jsonify(
                    {
                        "error": "Password must be at least 8 characters and contain letters and numbers"
                    }
                ),
                400,
            )

        # Get user
        user_id = payload.get("user_id")
        user_data = dynamoDB_client.get_item(key={'id': user_id})
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        user = User(**user_data)

        # Verify current password
        if not verify_password(current_password, user.passwordHash):
            return jsonify({"error": "Current password is incorrect"}), 400

        # Check if new password is different from current
        if verify_password(new_password, user.passwordHash):
            return (
                jsonify(
                    {"error": "New password must be different from current password"}
                ),
                400,
            )

        # Update password
        update_data = {
            'passwordHash': hash_password(new_password),
            'updatedAt': datetime.now().isoformat()
        }
        dynamoDB_client.update_item(key={'id': user_id}, update_data=update_data)

        return jsonify({"message": "Password has been changed successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Password change failed", "details": str(e)}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout user (client-side token removal)"""
    # Since we're using stateless JWTs, logout is handled client-side
    # In a more complex system, you might maintain a blacklist of tokens
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """Get current authenticated user data"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(" ")[1]

        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        # Get user
        user_id = payload.get("user_id")
        user_data = dynamoDB_client.get_item(key={'id': user_id})
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Convert Decimals before creating User object
        user_data = prepare_user_data_from_dynamo(user_data)
        user = User(**user_data)

        # Check if user is still active
        if not user.active:
            return jsonify({"error": "Account is deactivated"}), 401

        # Return user data
        user_data = user.to_public_dict()
        user_data["role_name"] = UserRole(user.role).name
        user_data["type_name"] = UserType(user.type).name
        
        # Ensure all Decimals are converted
        user_data = convert_decimals(user_data)

        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({"error": "Failed to get user data", "details": str(e)}), 500

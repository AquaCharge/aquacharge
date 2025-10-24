from functools import wraps
from flask import request, jsonify
import jwt

# Configuration
JWT_SECRET = "your-secret-key-change-in-production"  # Should match auth.py
JWT_ALGORITHM = "HS256"


def decode_jwt_token(token: str):
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def require_auth(f):
    """Decorator to require authentication for a route"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(" ")[1]

        try:
            # Decode token
            payload = decode_jwt_token(token)

            # Add user info to request context
            request.current_user = payload

            return f(*args, **kwargs)

        except ValueError as e:
            return jsonify({"error": str(e)}), 401
        except Exception:
            return jsonify({"error": "Authentication failed"}), 401

    return decorated_function


def require_role(required_role):
    """Decorator to require a specific role for a route"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not hasattr(request, "current_user"):
                return jsonify({"error": "Authentication required"}), 401

            user_role = request.current_user.get("role")

            # Role hierarchy: ADMIN (1) > OPERATOR (2) > USER (3)
            role_hierarchy = {1: "ADMIN", 2: "OPERATOR", 3: "USER"}
            required_role_value = None

            # Find required role value
            for value, name in role_hierarchy.items():
                if name == required_role:
                    required_role_value = value
                    break

            if required_role_value is None:
                return jsonify({"error": "Invalid role requirement"}), 500

            # Check if user has sufficient permissions
            if user_role > required_role_value:
                return jsonify({"error": "Insufficient permissions"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_current_user():
    """Get current user data from request context"""
    if hasattr(request, "current_user"):
        return request.current_user
    return None

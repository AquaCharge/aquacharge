from flask import Blueprint, jsonify, request, current_app
from models.user import User, UserRole
from datetime import datetime, timedelta
from typing import Dict, Any
import hashlib
import jwt
import secrets
import re

auth_bp = Blueprint('auth', __name__)

# In-memory storage for password reset tokens (replace with database in production)
password_reset_tokens: Dict[str, Dict[str, Any]] = {}

# Helper functions
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
        jwt_secret = current_app.config.get('JWT_SECRET_KEY', 'dev-jwt-secret-key')
        jwt_algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
        jwt_expiry = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=24))
    except RuntimeError:
        # Fallback for testing without app context
        jwt_secret = 'dev-jwt-secret-key'
        jwt_algorithm = 'HS256'
        jwt_expiry = timedelta(hours=24)
    
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + jwt_expiry,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        jwt_secret = current_app.config.get('JWT_SECRET_KEY', 'dev-jwt-secret-key')
        jwt_algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
    except RuntimeError:
        # Fallback for testing without app context
        jwt_secret = 'dev-jwt-secret-key'
        jwt_algorithm = 'HS256'
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError:
        raise ValueError('Invalid token')

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> bool:
    """Validate password strength"""
    # At least 8 characters, contains letters and numbers
    if len(password) < 8:
        return False
    if not re.search(r'[A-Za-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

# Routes
@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Import users database
        from api.users import users_db
        
        # Find user by email
        user = None
        for user_obj in users_db.values():
            if user_obj.email.lower() == email:
                user = user_obj
                break
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if user is active
        if not user.active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Verify password
        if not verify_password(password, user.passwordHash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token = generate_jwt_token(user)
        
        # Update last login time
        user.updatedAt = datetime.now()
        
        # Return user data (without password) and token
        user_data = user.to_public_dict()
        user_data['role_name'] = UserRole(user.role).name
        
        return jsonify({
            'token': token,
            'user': user_data,
            'expires_in': 24 * 3600  # 24 hours in seconds
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        username = data['username'].strip()
        email = data['email'].lower().strip()
        password = data['password']
        
        # Validate email format
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if not validate_password(password):
            return jsonify({'error': 'Password must be at least 8 characters and contain letters and numbers'}), 400
        
        # Import users database
        from api.users import users_db
        
        # Check if email already exists
        for user in users_db.values():
            if user.email.lower() == email:
                return jsonify({'error': 'Email already registered'}), 409
            if user.username.lower() == username.lower():
                return jsonify({'error': 'Username already taken'}), 409
        
        # Create new user
        user = User(
            username=username,
            email=email,
            passwordHash=hash_password(password),
            role=UserRole.USER.value,  # Default role
            active=True,
            orgId=data.get('orgId'),
            createdAt=datetime.now()
        )
        
        # Validate user data
        try:
            user.validate()
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Store user
        users_db[user.id] = user
        
        # Generate JWT token for auto-login
        token = generate_jwt_token(user)
        
        # Return user data (without password) and token
        user_data = user.to_public_dict()
        user_data['role_name'] = UserRole(user.role).name
        
        return jsonify({
            'token': token,
            'user': user_data,
            'message': 'Registration successful'
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify JWT token and return user data"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        # Import users database
        from api.users import users_db
        
        # Get user from database
        user_id = payload.get('user_id')
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user = users_db[user_id]
        
        # Check if user is still active
        if not user.active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Return user data
        user_data = user.to_public_dict()
        user_data['role_name'] = UserRole(user.role).name
        
        return jsonify({
            'user': user_data,
            'valid': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Token verification failed', 'details': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh JWT token"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decode token (even if expired)
        try:
            jwt_secret = current_app.config.get('JWT_SECRET_KEY', 'dev-jwt-secret-key')
            jwt_algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
        except RuntimeError:
            jwt_secret = 'dev-jwt-secret-key'
            jwt_algorithm = 'HS256'
            
        try:
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm], options={"verify_exp": False})
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Import users database
        from api.users import users_db
        
        # Get user from database
        user_id = payload.get('user_id')
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user = users_db[user_id]
        
        # Check if user is still active
        if not user.active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Generate new token
        new_token = generate_jwt_token(user)
        
        return jsonify({
            'token': new_token,
            'expires_in': 24 * 3600  # 24 hours in seconds
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Token refresh failed', 'details': str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset token"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
        
        email = data['email'].lower().strip()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Import users database
        from api.users import users_db
        
        # Find user by email
        user = None
        for user_obj in users_db.values():
            if user_obj.email.lower() == email:
                user = user_obj
                break
        
        # Always return success to prevent email enumeration
        # But only actually process if user exists
        if user and user.active:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            
            # Store reset token with expiry
            password_reset_tokens[reset_token] = {
                'user_id': user.id,
                'email': user.email,
                'expires_at': datetime.now() + timedelta(hours=2),  # 2 hours
                'used': False
            }
            
            # TODO: Send email with reset link
            # For now, we'll just log it (in production, integrate with email service)
            reset_link = f"https://aquacharge.com/reset-password?token={reset_token}"
            print(f"Password reset link for {email}: {reset_link}")
        
        return jsonify({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Password reset request failed', 'details': str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using reset token"""
    try:
        data = request.get_json()
        
        required_fields = ['token', 'new_password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Validate password strength
        if not validate_password(new_password):
            return jsonify({'error': 'Password must be at least 8 characters and contain letters and numbers'}), 400
        
        # Check if token exists and is valid
        if token not in password_reset_tokens:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        token_data = password_reset_tokens[token]
        
        # Check if token is expired
        if datetime.now() > token_data['expires_at']:
            del password_reset_tokens[token]
            return jsonify({'error': 'Reset token has expired'}), 400
        
        # Check if token was already used
        if token_data['used']:
            return jsonify({'error': 'Reset token has already been used'}), 400
        
        # Import users database
        from api.users import users_db
        
        # Get user
        user_id = token_data['user_id']
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user = users_db[user_id]
        
        # Update password
        user.passwordHash = hash_password(new_password)
        user.updatedAt = datetime.now()
        
        # Mark token as used
        token_data['used'] = True
        
        return jsonify({
            'message': 'Password has been reset successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Password reset failed', 'details': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change password for authenticated user"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        data = request.get_json()
        
        required_fields = ['current_password', 'new_password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate new password strength
        if not validate_password(new_password):
            return jsonify({'error': 'Password must be at least 8 characters and contain letters and numbers'}), 400
        
        # Import users database
        from api.users import users_db
        
        # Get user
        user_id = payload.get('user_id')
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user = users_db[user_id]
        
        # Verify current password
        if not verify_password(current_password, user.passwordHash):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Check if new password is different from current
        if verify_password(new_password, user.passwordHash):
            return jsonify({'error': 'New password must be different from current password'}), 400
        
        # Update password
        user.passwordHash = hash_password(new_password)
        user.updatedAt = datetime.now()
        
        return jsonify({
            'message': 'Password has been changed successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Password change failed', 'details': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user (client-side token removal)"""
    # Since we're using stateless JWTs, logout is handled client-side
    # In a more complex system, you might maintain a blacklist of tokens
    return jsonify({
        'message': 'Logged out successfully'
    }), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user data"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decode token
        try:
            payload = decode_jwt_token(token)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        # Import users database
        from api.users import users_db
        
        # Get user
        user_id = payload.get('user_id')
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user = users_db[user_id]
        
        # Check if user is still active
        if not user.active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Return user data
        user_data = user.to_public_dict()
        user_data['role_name'] = UserRole(user.role).name
        
        return jsonify(user_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user data', 'details': str(e)}), 500

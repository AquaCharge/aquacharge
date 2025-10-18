from flask import Blueprint, jsonify, request
from backend.models.user import User, UserRole
from datetime import datetime
from typing import Dict, Any
import hashlib

users_bp = Blueprint('users', __name__)

# In-memory storage (replace with actual database)
users_db: Dict[str, User] = {}

@users_bp.route('', methods=['GET'])
def get_users():
    """Get all users"""
    users_list = [user.to_public_dict() for user in users_db.values()]
    return jsonify(users_list), 200

@users_bp.route('/<user_id>', methods=['GET'])
def get_user(user_id: str):
    """Get a specific user by ID"""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(users_db[user_id].to_public_dict()), 200

@users_bp.route('', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create user instance
    user = User(
        username=data['username'],
        email=data['email'],
        passwordHash=hashlib.sha256(data['password'].encode()).hexdigest(),
        role=UserRole[data.get('role', 'USER')].value if 'role' in data else UserRole.USER.value,
        orgId=data.get('orgId')
    )
    
    # Validate user data
    try:
        user.validate()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Store user
    users_db[user.id] = user
    
    return jsonify(user.to_public_dict()), 201

@users_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id: str):
    """Update an existing user"""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    user = users_db[user_id]
    
    # Update allowed fields
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'role' in data:
        user.role = UserRole[data['role']].value
    if 'active' in data:
        user.active = data['active']
    if 'orgId' in data:
        user.orgId = data['orgId']
    
    user.updatedAt = datetime.now()
    
    # Validate updated user
    try:
        user.validate()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    return jsonify(user.to_public_dict()), 200

@users_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id: str):
    """Delete a user"""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    del users_db[user_id]
    return jsonify({'message': 'User deleted successfully'}), 200
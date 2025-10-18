from flask import Blueprint, jsonify, request
from backend.models.vessel import Vessel
from datetime import datetime
from typing import Dict

vessels_bp = Blueprint('vessels', __name__)

# In-memory storage (replace with actual database)
vessels_db: Dict[str, Vessel] = {}

@vessels_bp.route('', methods=['GET'])
def get_vessels():
    """Get all vessels, optionally filtered by userId"""
    user_id = request.args.get('userId')
    
    if user_id:
        vessels = [v.to_dict() for v in vessels_db.values() if v.userId == user_id]
    else:
        vessels = [v.to_dict() for v in vessels_db.values()]
    
    return jsonify(vessels), 200

@vessels_bp.route('/<vessel_id>', methods=['GET'])
def get_vessel(vessel_id: str):
    """Get a specific vessel by ID"""
    if vessel_id not in vessels_db:
        return jsonify({'error': 'Vessel not found'}), 404
    
    return jsonify(vessels_db[vessel_id].to_dict()), 200

@vessels_bp.route('', methods=['POST'])
def create_vessel():
    """Create a new vessel"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['userId', 'displayName', 'vesselType', 'chargerType', 'capacity']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create vessel instance
    vessel = Vessel(
        userId=data['userId'],
        displayName=data['displayName'],
        vesselType=data['vesselType'],
        chargerType=data['chargerType'],
        capacity=float(data['capacity']),
        maxChargeRate=float(data.get('maxChargeRate', 0)),
        minChargeRate=float(data.get('minChargeRate', 0)),
        rangeMeters=float(data.get('rangeMeters', 0))
    )
    
    # Store vessel
    vessels_db[vessel.id] = vessel
    
    return jsonify(vessel.to_dict()), 201

@vessels_bp.route('/<vessel_id>', methods=['PUT'])
def update_vessel(vessel_id: str):
    """Update an existing vessel"""
    if vessel_id not in vessels_db:
        return jsonify({'error': 'Vessel not found'}), 404
    
    data = request.get_json()
    vessel = vessels_db[vessel_id]
    
    # Update allowed fields
    update_fields = ['displayName', 'vesselType', 'chargerType', 'capacity', 
                     'maxChargeRate', 'minChargeRate', 'rangeMeters', 'active']
    
    for field in update_fields:
        if field in data:
            if field in ['capacity', 'maxChargeRate', 'minChargeRate', 'rangeMeters']:
                setattr(vessel, field, float(data[field]))
            else:
                setattr(vessel, field, data[field])
    
    vessel.updatedAt = datetime.now()
    
    return jsonify(vessel.to_dict()), 200

@vessels_bp.route('/<vessel_id>', methods=['DELETE'])
def delete_vessel(vessel_id: str):
    """Delete a vessel"""
    if vessel_id not in vessels_db:
        return jsonify({'error': 'Vessel not found'}), 404
    
    del vessels_db[vessel_id]
    return jsonify({'message': 'Vessel deleted successfully'}), 200
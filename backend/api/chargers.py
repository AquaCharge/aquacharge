from flask import Blueprint, jsonify, request
from backend.models.charger import Charger, ChargerStatus
from typing import Dict

chargers_bp = Blueprint('chargers', __name__)

# In-memory storage (replace with actual database)
chargers_db: Dict[str, Charger] = {}

@chargers_bp.route('', methods=['GET'])
def get_chargers():
    """Get all chargers, optionally filtered by station"""
    station_id = request.args.get('stationId')
    
    if station_id:
        chargers = [c.to_dict() for c in chargers_db.values() 
                   if c.chargingStationId == station_id]
    else:
        chargers = [c.to_dict() for c in chargers_db.values()]
    
    return jsonify(chargers), 200

@chargers_bp.route('/<charger_id>', methods=['GET'])
def get_charger(charger_id: str):
    """Get a specific charger by ID"""
    if charger_id not in chargers_db:
        return jsonify({'error': 'Charger not found'}), 404
    
    return jsonify(chargers_db[charger_id].to_dict()), 200

@chargers_bp.route('', methods=['POST'])
def create_charger():
    """Create a new charger"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['chargingStationId', 'chargerType', 'maxRate']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create charger instance
    charger = Charger(
        chargingStationId=data['chargingStationId'],
        chargerType=data['chargerType'],
        maxRate=float(data['maxRate']),
        active=data.get('active', True)
    )
    
    # Store charger
    chargers_db[charger.id] = charger
    
    return jsonify(charger.to_dict()), 201

@chargers_bp.route('/<charger_id>', methods=['PUT'])
def update_charger(charger_id: str):
    """Update an existing charger"""
    if charger_id not in chargers_db:
        return jsonify({'error': 'Charger not found'}), 404
    
    data = request.get_json()
    charger = chargers_db[charger_id]
    
    # Update allowed fields
    if 'chargerType' in data:
        charger.chargerType = data['chargerType']
    if 'maxRate' in data:
        charger.maxRate = float(data['maxRate'])
    if 'active' in data:
        charger.active = data['active']
    
    return jsonify(charger.to_dict()), 200

@chargers_bp.route('/<charger_id>', methods=['DELETE'])
def delete_charger(charger_id: str):
    """Delete a charger"""
    if charger_id not in chargers_db:
        return jsonify({'error': 'Charger not found'}), 404
    
    del chargers_db[charger_id]
    return jsonify({'message': 'Charger deleted successfully'}), 200

@chargers_bp.route('/available', methods=['GET'])
def get_available_chargers():
    """Get available chargers at a station"""
    station_id = request.args.get('stationId')
    charger_type = request.args.get('chargerType')
    
    chargers = [c for c in chargers_db.values() if c.active]
    
    if station_id:
        chargers = [c for c in chargers if c.chargingStationId == station_id]
    
    if charger_type:
        chargers = [c for c in chargers if c.chargerType == charger_type]
    
    return jsonify([c.to_dict() for c in chargers]), 200
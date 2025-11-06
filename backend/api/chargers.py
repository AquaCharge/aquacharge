from flask import Blueprint, jsonify, request
from models.charger import Charger
from typing import Dict

chargers_bp = Blueprint("chargers", __name__)

# In-memory storage (replace with actual database)
chargers_db: Dict[str, Charger] = {}


# Initialize with sample data
def init_sample_chargers():
    if not chargers_db:  # Only initialize if empty
        sample_chargers = [
            # Marina Bay Charging Hub chargers
            Charger(
                id="charger-001",
                chargingStationId="station-001",
                chargerType="Type 2 AC",
                maxRate=22.0,
                active=True,
            ),
            Charger(
                id="charger-002",
                chargingStationId="station-001",
                chargerType="CCS DC",
                maxRate=50.0,
                active=True,
            ),
            Charger(
                id="charger-003",
                chargingStationId="station-001",
                chargerType="CHAdeMO",
                maxRate=50.0,
                active=True,
            ),
            # Harbour View Electric Dock chargers
            Charger(
                id="charger-004",
                chargingStationId="station-002",
                chargerType="Type 2 AC",
                maxRate=11.0,
                active=True,
            ),
            Charger(
                id="charger-005",
                chargingStationId="station-002",
                chargerType="CCS DC",
                maxRate=75.0,
                active=True,
            ),
            # Blue Water Marina Station chargers
            Charger(
                id="charger-006",
                chargingStationId="station-003",
                chargerType="Type 2 AC",
                maxRate=22.0,
                active=False,
            ),
            Charger(
                id="charger-007",
                chargingStationId="station-003",
                chargerType="Tesla Supercharger",
                maxRate=120.0,
                active=False,
            ),
            # Nordic Fjord Charging Point chargers
            Charger(
                id="charger-008",
                chargingStationId="station-004",
                chargerType="Type 2 AC",
                maxRate=22.0,
                active=True,
            ),
            Charger(
                id="charger-009",
                chargingStationId="station-004",
                chargerType="CCS DC",
                maxRate=100.0,
                active=True,
            ),
            # Mediterranean Charging Hub chargers
            Charger(
                id="charger-010",
                chargingStationId="station-006",
                chargerType="Type 2 AC",
                maxRate=7.4,
                active=True,
            ),
            Charger(
                id="charger-011",
                chargingStationId="station-006",
                chargerType="CCS DC",
                maxRate=50.0,
                active=True,
            ),
            Charger(
                id="charger-012",
                chargingStationId="station-006",
                chargerType="CHAdeMO",
                maxRate=50.0,
                active=True,
            ),
        ]

        for charger in sample_chargers:
            chargers_db[charger.id] = charger


# Initialize sample data when module is imported
init_sample_chargers()


@chargers_bp.route("", methods=["GET"])
def get_chargers():
    """Get all chargers, optionally filtered by station"""
    station_id = request.args.get("stationId")

    if station_id:
        chargers = [
            c.to_dict()
            for c in chargers_db.values()
            if c.chargingStationId == station_id
        ]
    else:
        chargers = [c.to_dict() for c in chargers_db.values()]

    return jsonify(chargers), 200


@chargers_bp.route("/<charger_id>", methods=["GET"])
def get_charger(charger_id: str):
    """Get a specific charger by ID"""
    if charger_id not in chargers_db:
        return jsonify({"error": "Charger not found"}), 404

    return jsonify(chargers_db[charger_id].to_dict()), 200


@chargers_bp.route("", methods=["POST"])
def create_charger():
    """Create a new charger"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["chargingStationId", "chargerType", "maxRate"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Create charger instance
    charger = Charger(
        chargingStationId=data["chargingStationId"],
        chargerType=data["chargerType"],
        maxRate=float(data["maxRate"]),
        active=data.get("active", True),
    )

    # Store charger
    chargers_db[charger.id] = charger

    return jsonify(charger.to_dict()), 201


@chargers_bp.route("/<charger_id>", methods=["PUT"])
def update_charger(charger_id: str):
    """Update an existing charger"""
    if charger_id not in chargers_db:
        return jsonify({"error": "Charger not found"}), 404

    data = request.get_json()
    charger = chargers_db[charger_id]

    # Update allowed fields
    if "chargerType" in data:
        charger.chargerType = data["chargerType"]
    if "maxRate" in data:
        charger.maxRate = float(data["maxRate"])
    if "active" in data:
        charger.active = data["active"]

    return jsonify(charger.to_dict()), 200


@chargers_bp.route("/<charger_id>", methods=["DELETE"])
def delete_charger(charger_id: str):
    """Delete a charger"""
    if charger_id not in chargers_db:
        return jsonify({"error": "Charger not found"}), 404

    del chargers_db[charger_id]
    return jsonify({"message": "Charger deleted successfully"}), 200


@chargers_bp.route("/available", methods=["GET"])
def get_available_chargers():
    """Get available chargers at a station"""
    station_id = request.args.get("stationId")
    charger_type = request.args.get("chargerType")

    chargers = [c for c in chargers_db.values() if c.active]

    if station_id:
        chargers = [c for c in chargers if c.chargingStationId == station_id]

    if charger_type:
        chargers = [c for c in chargers if c.chargerType == charger_type]

    return jsonify([c.to_dict() for c in chargers]), 200

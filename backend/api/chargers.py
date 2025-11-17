from flask import Blueprint, jsonify, request
from models.charger import Charger
import decimal
from db.dynamoClient import DynamoClient

chargers_bp = Blueprint("chargers", __name__)

dynamoDB_client = DynamoClient(
    table_name="aquacharge-chargers-dev", region_name="us-east-1"
)


@chargers_bp.route("", methods=["GET"])
def get_chargers():
    """Get all chargers, optionally filtered by station"""
    station_id = request.args.get("stationId")

    chargers = dynamoDB_client.scan_items()

    if station_id:
        chargers = [c.to_dict() for c in chargers if c.chargingStationId == station_id]

    return jsonify(chargers), 200


@chargers_bp.route("/<charger_id>", methods=["GET"])
def get_charger(charger_id: str):
    """Get a specific charger by ID"""
    charger = dynamoDB_client.get_item(key={"id": charger_id})
    if not charger:
        return jsonify({"error": "Charger not found"}), 404

    return jsonify(charger), 200


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
        maxRate=decimal.Decimal(data["maxRate"]),
        active=data.get("active", True),
    )

    # Store charger
    dynamoDB_client.put_item(item=charger.to_dict())

    return jsonify(charger.to_dict()), 201


@chargers_bp.route("/<charger_id>", methods=["PUT"])
def update_charger(charger_id: str):
    """Update an existing charger"""
    charger_dict = dynamoDB_client.get_item(key={"id": charger_id})
    if not charger_dict:
        return jsonify({"error": "Charger not found"}), 404

    data = request.get_json()

    charger = Charger(**charger_dict)
    # Update allowed fields
    if "chargerType" in data:
        charger.chargerType = data["chargerType"]
    if "maxRate" in data:
        charger.maxRate = decimal.Decimal(data["maxRate"])
    if "active" in data:
        charger.active = data["active"]

    dynamoDB_client.put_item(item=charger.to_dict())
    return jsonify(charger.to_dict()), 200


@chargers_bp.route("/<charger_id>", methods=["DELETE"])
def delete_charger(charger_id: str):
    """Delete a charger"""
    charger = dynamoDB_client.get_item(key={"id": charger_id})
    if not charger:
        return jsonify({"error": "Charger not found"}), 404

    dynamoDB_client.delete_item(key={"id": charger_id})
    return jsonify({"message": "Charger deleted successfully"}), 200


@chargers_bp.route("/available", methods=["GET"])
def get_available_chargers():
    """Get available chargers at a station"""
    station_id = request.args.get("stationId")
    charger_type = request.args.get("chargerType")

    chargers = dynamoDB_client.scan_items()
    chargers = [c for c in chargers if c["active"]]

    if station_id:
        chargers = [c for c in chargers if c["chargingStationId"] == station_id]

    if charger_type:
        chargers = [c for c in chargers if c["chargerType"] == charger_type]

    return jsonify(chargers), 200

from flask import Blueprint, jsonify, request
from models.vessel import Vessel
from datetime import datetime
from db.dynamodb import db_client

vessels_bp = Blueprint("vessels", __name__)


@vessels_bp.route("", methods=["GET"])
def get_vessels():
    """Get all vessels, optionally filtered by userId"""
    try:
        user_id = request.args.get("userId")

        if user_id:
            vessels_data = db_client.get_vessels_by_user(user_id)
        else:
            vessels_data = db_client.scan_table(
                db_client.vessels_table_name, limit=1000
            )

        vessels = [Vessel.from_dict(v).to_dict() for v in vessels_data]
        return jsonify(vessels), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch vessels", "details": str(e)}), 500


@vessels_bp.route("/<vessel_id>", methods=["GET"])
def get_vessel(vessel_id: str):
    """Get a specific vessel by ID"""
    try:
        vessel_data = db_client.get_vessel_by_id(vessel_id)

        if not vessel_data:
            return jsonify({"error": "Vessel not found"}), 404

        vessel = Vessel.from_dict(vessel_data)
        return jsonify(vessel.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch vessel", "details": str(e)}), 500


@vessels_bp.route("", methods=["POST"])
def create_vessel():
    """Create a new vessel"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "userId",
            "displayName",
            "vesselType",
            "chargerType",
            "capacity",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Create vessel instance
        vessel = Vessel(
            userId=data["userId"],
            displayName=data["displayName"],
            vesselType=data["vesselType"],
            chargerType=data["chargerType"],
            capacity=float(data["capacity"]),
            maxChargeRate=float(data.get("maxChargeRate", 0)),
            minChargeRate=float(data.get("minChargeRate", 0)),
            rangeMeters=float(data.get("rangeMeters", 0)),
        )

        # Store vessel in DynamoDB
        db_client.create_vessel(vessel.to_dict())

        return jsonify(vessel.to_dict()), 201
    except Exception as e:
        return jsonify({"error": "Failed to create vessel", "details": str(e)}), 500


@vessels_bp.route("/<vessel_id>", methods=["PUT"])
def update_vessel(vessel_id: str):
    """Update an existing vessel"""
    try:
        vessel_data = db_client.get_vessel_by_id(vessel_id)

        if not vessel_data:
            return jsonify({"error": "Vessel not found"}), 404

        data = request.get_json()
        vessel = Vessel.from_dict(vessel_data)

        # Update allowed fields
        update_fields = [
            "displayName",
            "vesselType",
            "chargerType",
            "capacity",
            "maxChargeRate",
            "minChargeRate",
            "rangeMeters",
            "active",
        ]

        for field in update_fields:
            if field in data:
                if field in [
                    "capacity",
                    "maxChargeRate",
                    "minChargeRate",
                    "rangeMeters",
                ]:
                    setattr(vessel, field, float(data[field]))
                else:
                    setattr(vessel, field, data[field])

        vessel.updatedAt = datetime.now()

        # Update in DynamoDB
        db_client.put_item(db_client.vessels_table_name, vessel.to_dict())

        return jsonify(vessel.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to update vessel", "details": str(e)}), 500


@vessels_bp.route("/<vessel_id>", methods=["DELETE"])
def delete_vessel(vessel_id: str):
    """Delete a vessel"""
    try:
        vessel_data = db_client.get_vessel_by_id(vessel_id)

        if not vessel_data:
            return jsonify({"error": "Vessel not found"}), 404

        db_client.delete_item(db_client.vessels_table_name, {"id": vessel_id})
        return jsonify({"message": "Vessel deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete vessel", "details": str(e)}), 500

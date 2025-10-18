from flask import Blueprint, jsonify, request
from backend.models.vessel import Vessel
from datetime import datetime
from typing import Dict

vessels_bp = Blueprint("vessels", __name__)

# In-memory storage (replace with actual database)
vessels_db: Dict[str, Vessel] = {}


# Initialize with sample data
def init_sample_vessels():
    if not vessels_db:  # Only initialize if empty
        sample_vessels = [
            Vessel(
                id="vessel-001",
                userId="user-003",
                displayName="Ocean Breeze",
                vesselType="Sailing Yacht",
                chargerType="Type 2 AC",
                capacity=80.0,
                maxChargeRate=22.0,
                minChargeRate=3.7,
                rangeMeters=185200.0,  # ~100 nautical miles
                active=True,
                createdAt=datetime(2024, 3, 6, 10, 0, 0),
                updatedAt=datetime(2024, 3, 15, 14, 30, 0),
            ),
            Vessel(
                id="vessel-002",
                userId="user-003",
                displayName="Sea Runner",
                vesselType="Motor Yacht",
                chargerType="CCS DC",
                capacity=150.0,
                maxChargeRate=50.0,
                minChargeRate=7.0,
                rangeMeters=370400.0,  # ~200 nautical miles
                active=True,
                createdAt=datetime(2024, 3, 8, 16, 45, 0),
                updatedAt=None,
            ),
            Vessel(
                id="vessel-003",
                userId="user-004",
                displayName="Royal Wind",
                vesselType="Catamaran",
                chargerType="Type 2 AC",
                capacity=120.0,
                maxChargeRate=11.0,
                minChargeRate=3.7,
                rangeMeters=277800.0,  # ~150 nautical miles
                active=True,
                createdAt=datetime(2024, 1, 25, 9, 15, 0),
                updatedAt=datetime(2024, 2, 10, 11, 20, 0),
            ),
            Vessel(
                id="vessel-004",
                userId="user-005",
                displayName="Fleet Alpha",
                vesselType="Commercial Vessel",
                chargerType="CCS DC",
                capacity=300.0,
                maxChargeRate=120.0,
                minChargeRate=25.0,
                rangeMeters=555600.0,  # ~300 nautical miles
                active=False,
                createdAt=datetime(2024, 4, 2, 8, 30, 0),
                updatedAt=datetime(2024, 4, 10, 13, 45, 0),
            ),
            Vessel(
                id="vessel-005",
                userId="user-005",
                displayName="Fleet Beta",
                vesselType="Commercial Vessel",
                chargerType="CHAdeMO",
                capacity=250.0,
                maxChargeRate=50.0,
                minChargeRate=20.0,
                rangeMeters=463000.0,  # ~250 nautical miles
                active=True,
                createdAt=datetime(2024, 4, 3, 12, 0, 0),
                updatedAt=None,
            ),
            Vessel(
                id="vessel-006",
                userId="user-002",
                displayName="Harbor Patrol",
                vesselType="Work Boat",
                chargerType="Type 2 AC",
                capacity=60.0,
                maxChargeRate=22.0,
                minChargeRate=7.4,
                rangeMeters=92600.0,  # ~50 nautical miles
                active=True,
                createdAt=datetime(2024, 2, 15, 7, 30, 0),
                updatedAt=datetime(2024, 3, 1, 15, 10, 0),
            ),
        ]

        for vessel in sample_vessels:
            vessels_db[vessel.id] = vessel


# Initialize sample data when module is imported
init_sample_vessels()


@vessels_bp.route("", methods=["GET"])
def get_vessels():
    """Get all vessels, optionally filtered by userId"""
    user_id = request.args.get("userId")

    if user_id:
        vessels = [v.to_dict() for v in vessels_db.values() if v.userId == user_id]
    else:
        vessels = [v.to_dict() for v in vessels_db.values()]

    return jsonify(vessels), 200


@vessels_bp.route("/<vessel_id>", methods=["GET"])
def get_vessel(vessel_id: str):
    """Get a specific vessel by ID"""
    if vessel_id not in vessels_db:
        return jsonify({"error": "Vessel not found"}), 404

    return jsonify(vessels_db[vessel_id].to_dict()), 200


@vessels_bp.route("", methods=["POST"])
def create_vessel():
    """Create a new vessel"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["userId", "displayName", "vesselType", "chargerType", "capacity"]
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

    # Store vessel
    vessels_db[vessel.id] = vessel

    return jsonify(vessel.to_dict()), 201


@vessels_bp.route("/<vessel_id>", methods=["PUT"])
def update_vessel(vessel_id: str):
    """Update an existing vessel"""
    if vessel_id not in vessels_db:
        return jsonify({"error": "Vessel not found"}), 404

    data = request.get_json()
    vessel = vessels_db[vessel_id]

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
            if field in ["capacity", "maxChargeRate", "minChargeRate", "rangeMeters"]:
                setattr(vessel, field, float(data[field]))
            else:
                setattr(vessel, field, data[field])

    vessel.updatedAt = datetime.now()

    return jsonify(vessel.to_dict()), 200


@vessels_bp.route("/<vessel_id>", methods=["DELETE"])
def delete_vessel(vessel_id: str):
    """Delete a vessel"""
    if vessel_id not in vessels_db:
        return jsonify({"error": "Vessel not found"}), 404

    del vessels_db[vessel_id]
    return jsonify({"message": "Vessel deleted successfully"}), 200

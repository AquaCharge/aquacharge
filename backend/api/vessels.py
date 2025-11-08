from flask import Blueprint, jsonify, request
from models.vessel import Vessel
from datetime import datetime
from db.dynamoClient import DynamoClient
import decimal

dynamoDB_client = DynamoClient(
    table_name="aquacharge-vessels-dev", region_name="us-east-1"
)

vessels_bp = Blueprint("vessels", __name__)


@vessels_bp.route("", methods=["GET"])
def get_vessels():
    """Get all vessels, optionally filtered by userId"""
    user_id = request.args.get("userId")

    if user_id:
        vessels = dynamoDB_client.query_gsi(
            index_name="userId-index",
            key_condition_expression="userId = :userId",
            expression_attribute_values={":userId": user_id},
        )
    else:
        vessels = dynamoDB_client.scan_items()

    return jsonify(vessels), 200


@vessels_bp.route("/<vessel_id>", methods=["GET"])
def get_vessel(vessel_id: str):
    """Get a specific vessel by ID"""
    vessel = dynamoDB_client.get_item({"id": vessel_id})
    if not vessel:
        return jsonify({"error": "Vessel not found"}), 404

    return jsonify(vessel), 200


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
        maxChargeRate=decimal.Decimal(data.get("maxChargeRate", 0)),
        minChargeRate=decimal.Decimal(data.get("minChargeRate", 0)),
        rangeMeters=decimal.Decimal(data.get("rangeMeters", 0)),
    )

    # Store vessel
    dynamoDB_client.put_item(vessel.to_dict())

    return jsonify(vessel.to_dict()), 201


@vessels_bp.route("/<vessel_id>", methods=["PUT"])
def update_vessel(vessel_id: str):
    """Update an existing vessel"""
    # Get vessel from database
    vessel_data = dynamoDB_client.get_item(key={"id": vessel_id})
    if not vessel_data:
        return jsonify({"error": "Vessel not found"}), 404

    data = request.get_json()

    # Create current vessel object
    current_vessel = Vessel(**vessel_data)

    # Define allowed fields and their types
    allowed_fields = {
        "displayName": str,
        "vesselType": str,
        "chargerType": str,
        "capacity": float,
        "maxChargeRate": decimal.Decimal,
        "minChargeRate": decimal.Decimal,
        "rangeMeters": decimal.Decimal,
        "active": bool,
    }

    # Build update dictionary dynamically
    update_data = {}
    for field, field_type in allowed_fields.items():
        if field in data:
            value = (
                field_type(data[field]) if field_type in [float, int] else data[field]
            )
            update_data[field] = value
            setattr(current_vessel, field, value)

    # Always update the timestamp
    update_data["updatedAt"] = datetime.now().isoformat()
    current_vessel.updatedAt = datetime.now()

    # Update the item in DynamoDB
    updated_vessel_dict = dynamoDB_client.update_item(
        key={"id": vessel_id}, update_data=update_data
    )

    updated_vessel = Vessel(**updated_vessel_dict)
    return jsonify(updated_vessel.to_dict()), 200


@vessels_bp.route("/<vessel_id>", methods=["DELETE"])
def delete_vessel(vessel_id: str):
    """Delete a vessel"""
    vessel = dynamoDB_client.get_item({"id": vessel_id})
    if not vessel:
        return jsonify({"error": "Vessel not found"}), 404

    dynamoDB_client.delete_item({"id": vessel_id})
    return jsonify({"message": "Vessel deleted successfully"}), 200

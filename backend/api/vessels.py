import decimal
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from flask import Blueprint, jsonify, request

import config
from db.dynamoClient import DynamoClient
from models.vessel import Vessel

dynamoDB_client = DynamoClient(
    table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
)
_measurements_client = DynamoClient(
    table_name=config.MEASUREMENTS_TABLE, region_name=config.AWS_REGION
)

vessels_bp = Blueprint("vessels", __name__)


def _parse_measurement_timestamp(item: dict):
    raw = item.get("timestamp") or item.get("createdAt")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_soc_by_vessel_id() -> dict:
    latest_soc = {}
    try:
        measurements = _measurements_client.scan_items()
    except Exception:
        return latest_soc

    for measurement in measurements:
        vessel_id = measurement.get("vesselId")
        if not vessel_id:
            continue

        soc = _to_float(measurement.get("currentSOC"))
        if soc is None:
            continue

        timestamp = _parse_measurement_timestamp(measurement)
        if timestamp is None:
            continue

        current_best = latest_soc.get(vessel_id)
        if current_best is None or timestamp > current_best["timestamp"]:
            latest_soc[vessel_id] = {"timestamp": timestamp, "soc": soc}

    return {
        vessel_id: payload["soc"] for vessel_id, payload in latest_soc.items()
    }


def _enrich_vessel_payload(vessel: dict, latest_soc_lookup: dict) -> dict:
    enriched = dict(vessel)
    latest_soc = latest_soc_lookup.get(enriched.get("id"))
    if latest_soc is None:
        return enriched

    enriched["currentSoc"] = round(latest_soc, 2)

    max_capacity = _to_float(enriched.get("maxCapacity"))
    if max_capacity is not None and max_capacity > 0:
        enriched["capacity"] = round((max_capacity * latest_soc) / 100.0, 4)

    return enriched


@vessels_bp.route("", methods=["GET"])
def get_vessels():
    """Get all vessels, optionally filtered by userId"""
    user_id = request.args.get("userId")

    if user_id:
        vessels = dynamoDB_client.query_gsi(
            index_name="userId-index",
            key_condition_expression=Key("userId").eq(user_id),
        )
    else:
        vessels = dynamoDB_client.scan_items()

    latest_soc_lookup = _latest_soc_by_vessel_id()
    vessels = [
        _enrich_vessel_payload(vessel, latest_soc_lookup)
        for vessel in vessels
    ]

    return jsonify(vessels), 200


@vessels_bp.route("/<vessel_id>", methods=["GET"])
def get_vessel(vessel_id: str):
    """Get a specific vessel by ID"""
    vessel = dynamoDB_client.get_item({"id": vessel_id})
    if not vessel:
        return jsonify({"error": "Vessel not found"}), 404

    vessel = _enrich_vessel_payload(vessel, _latest_soc_by_vessel_id())

    return jsonify(vessel), 200


@vessels_bp.route("", methods=["POST"])
def create_vessel():
    """Create a new vessel"""
    data = request.get_json()

    # Validate required fields
    required_fields = [
        "userId",
        "displayName",
        "vesselType",
        "chargerType",
        "capacity",
        "maxCapacity",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    capacity_val = decimal.Decimal(str(data["capacity"]))
    max_capacity_val = decimal.Decimal(str(data["maxCapacity"]))
    if capacity_val > max_capacity_val:
        return jsonify({"error": "capacity must not exceed maxCapacity"}), 400

    # Create vessel instance
    vessel = Vessel(
        userId=data["userId"],
        displayName=data["displayName"],
        vesselType=data["vesselType"],
        chargerType=data["chargerType"],
        capacity=float(capacity_val),
        maxCapacity=float(max_capacity_val),
        maxChargeRate=decimal.Decimal(data.get("maxChargeRate", 0)),
        minChargeRate=decimal.Decimal(data.get("minChargeRate", 0)),
        rangeMeters=decimal.Decimal(data.get("rangeMeters", 0)),
    )

    # Store vessel (DynamoDB requires Decimal for numeric attributes)
    vessel_dict = vessel.to_dict()
    vessel_dict["capacity"] = capacity_val
    vessel_dict["maxCapacity"] = max_capacity_val
    numeric_keys = (
        "maxChargeRate",
        "minChargeRate",
        "maxDischargeRate",
        "longitude",
        "latitude",
        "rangeMeters",
    )
    for key in numeric_keys:
        if key in vessel_dict and vessel_dict[key] is not None:
            vessel_dict[key] = decimal.Decimal(str(vessel_dict[key]))
    dynamoDB_client.put_item(vessel_dict)

    # Prepare response: convert Decimal fields back to native types for JSON
    resp = vessel.to_dict()
    try:
        if isinstance(resp.get("capacity"), decimal.Decimal):
            resp["capacity"] = float(resp["capacity"])
        if isinstance(resp.get("maxCapacity"), decimal.Decimal):
            resp["maxCapacity"] = float(resp["maxCapacity"])
    except Exception:
        pass

    return jsonify(resp), 201


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
        "capacity": decimal.Decimal,
        "maxCapacity": decimal.Decimal,
        "maxChargeRate": decimal.Decimal,
        "minChargeRate": decimal.Decimal,
        "rangeMeters": decimal.Decimal,
        "active": bool,
    }

    # Build update dictionary dynamically
    update_data = {}
    for field, field_type in allowed_fields.items():
        if field in data:
            if field_type == decimal.Decimal:
                value = decimal.Decimal(str(data[field]))
            elif field_type in [float, int]:
                value = field_type(data[field])
            else:
                value = data[field]
            update_data[field] = value
            setattr(
                current_vessel,
                field,
                float(value) if field_type == decimal.Decimal else value,
            )

    # Enforce capacity <= maxCapacity (use current vessel state after updates)
    cap = getattr(current_vessel, "capacity", 0) or 0
    max_cap = getattr(current_vessel, "maxCapacity", 0) or 0
    if max_cap > 0 and cap > max_cap:
        return jsonify({"error": "capacity must not exceed maxCapacity"}), 400

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

from flask import Blueprint, jsonify, request
from models.drevent import DREvent, EventStatus
from middleware.auth import require_auth, require_role
from datetime import datetime
from db.dynamoClient import DynamoClient
from decimal import Decimal

drevents_bp = Blueprint("drevents", __name__)


dynamoDB_client = DynamoClient(
    table_name="aquacharge-drevents-dev", region_name="us-east-1"
)


@drevents_bp.route("", methods=["GET"])
@require_auth
def get_drevents():
    """Get all DR events, optionally filtered by status"""
    try:
        # Get query parameters
        status_filter = request.args.get("status")
        drevents = dynamoDB_client.scan_items()

        # Filter events
        filtered_events = []
        for event in drevents:
            if status_filter and event["status"] != status_filter:
                continue
            drevent = DREvent.from_dict(event)
            filtered_events.append(drevent.to_dict())

        # Sort by start time (soonest first)
        filtered_events.sort(key=lambda x: x["startTime"])

        return jsonify(filtered_events), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve DR events", "details": str(e)}),
            500,
        )


@drevents_bp.route("/<event_id>", methods=["GET"])
@require_auth
def get_drevent_by_id(event_id):
    """Get a specific DR event by ID"""
    try:
        item = dynamoDB_client.get_item(key={"id": event_id})
        if not item:
            return jsonify({"error": "DR event not found"}), 404
        drevent = DREvent.from_dict(item)
        return jsonify(drevent.to_dict()), 200
    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve DR event", "details": str(e)}),
            500,
        )


@drevents_bp.route("", methods=["POST"])
@require_auth
@require_role("ADMIN")
def create_drevent():
    """Create a new DR event"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["stationId", "pricePerKwh", "targetEnergyKwh", "maxParticipants", "startTime", "endTime"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Create DR event instance
        drevent = DREvent(
            stationId=data["stationId"],
            pricePerKwh=Decimal(str(data["pricePerKwh"])),
            targetEnergyKwh=Decimal(str(data["targetEnergyKwh"])),
            maxParticipants=data["maxParticipants"],
            startTime=datetime.fromisoformat(data["startTime"]),
            endTime=datetime.fromisoformat(data["endTime"]),
            status=EventStatus.SCHEDULED.value,
            details=data.get("details", {}),
        )

        # Store DR event
        dynamoDB_client.put_item(item=drevent.to_dict())

        return jsonify(drevent.to_dict()), 201

    except Exception as e:
        return (
            jsonify({"error": "Failed to create DR event", "details": str(e)}),
            500,
        )


@drevents_bp.route("/<event_id>", methods=["PUT"])
@require_auth
def update_drevent(event_id):
    """Update an existing DR event"""
    try:
        item = dynamoDB_client.get_item(key={"id": event_id})
        if not item:
            return jsonify({"error": "DR event not found"}), 404

        data = request.get_json()
        drevent = DREvent.from_dict(item)

        # Update allowed fields
        if "pricePerKwh" in data:
            drevent.pricePerKwh = Decimal(str(data["pricePerKwh"]))
        if "targetEnergyKwh" in data:
            drevent.targetEnergyKwh = Decimal(str(data["targetEnergyKwh"]))
        if "maxParticipants" in data:
            drevent.maxParticipants = data["maxParticipants"]
        if "startTime" in data:
            drevent.startTime = datetime.fromisoformat(data["startTime"])
        if "endTime" in data:
            drevent.endTime = datetime.fromisoformat(data["endTime"])
        if "status" in data and data["status"] in EventStatus._value2member_map_:
            drevent.status = data["status"]
        if "details" in data:
            drevent.details = data["details"]

        # Store updated DR event
        dynamoDB_client.put_item(item=drevent.to_dict())

        return jsonify(drevent.to_dict()), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to update DR event", "details": str(e)}),
            500,
        )


@drevents_bp.route("/<event_id>", methods=["PUT"])
@require_auth
def cancel_drevent(event_id):
    """Cancel a DR event"""
    try:
        item = dynamoDB_client.get_item(key={"id": event_id})
        if not item:
            return jsonify({"error": "DR event not found"}), 404

        # Update the status to cancelled
        dynamoDB_client.update_item(
            key={"id": event_id},
            update_data={"status": EventStatus.CANCELLED.value}
        )
        return jsonify({"message": "DR event cancelled successfully"}), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to cancel DR event", "details": str(e)}),
            500,
        )

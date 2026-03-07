from flask import Blueprint, jsonify, request
from models.drevent import DREvent, EventStatus
from middleware.auth import require_auth, require_role
from datetime import datetime, timezone
from db.dynamoClient import DynamoClient
from decimal import Decimal
from services.eligibility import EligibilityService
from services.dr.dispatcher import _dispatch_loop

drevents_bp = Blueprint("drevents", __name__)


dynamoDB_client = DynamoClient(
    table_name="aquacharge-drevents-dev", region_name="us-east-1"
)
eligibility_service = EligibilityService()


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def serialize_drevent_item(event):
    """Normalize a DREvent item from Dynamo for API responses."""
    serialized = convert_decimals(dict(event))

    for field in ("startTime", "endTime", "createdAt"):
        value = serialized.get(field)
        if isinstance(value, datetime):
            serialized[field] = value.isoformat()

    status = serialized.get("status")
    if isinstance(status, EventStatus):
        serialized["status"] = status.value

    return serialized


def sort_key_for_drevent(event):
    start_time = event.get("startTime")
    if isinstance(start_time, str):
        try:
            parsed = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return datetime.max.replace(tzinfo=timezone.utc)
    if isinstance(start_time, datetime):
        if start_time.tzinfo is None:
            return start_time.replace(tzinfo=timezone.utc)
        return start_time.astimezone(timezone.utc)
    return datetime.max.replace(tzinfo=timezone.utc)


@drevents_bp.route("", methods=["GET"])
@require_auth
def get_drevents():
    """Get all DR events, optionally filtered by status"""
    try:
        # Get query parameters
        status_filter = request.args.get("status")
        drevents = dynamoDB_client.scan_items()

        filtered_events = []
        for event in drevents:
            normalized_event = serialize_drevent_item(event)
            if status_filter and normalized_event.get("status") != status_filter:
                continue
            filtered_events.append(normalized_event)

        filtered_events.sort(key=sort_key_for_drevent)

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
        return jsonify(serialize_drevent_item(item)), 200
    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve DR event", "details": str(e)}),
            500,
        )


@drevents_bp.route("/<event_id>/eligibility", methods=["GET"])
@require_auth
def get_drevent_eligibility(event_id):
    """Evaluate vessel eligibility for a specific DR event"""
    try:
        event = dynamoDB_client.get_item(key={"id": event_id})
        if not event:
            return jsonify({"error": "DR event not found"}), 404

        include_ineligible = (
            request.args.get("includeIneligible", "false").strip().lower() == "true"
        )
        eligibility_result = eligibility_service.evaluate_vessels_for_event(
            event,
            include_ineligible=include_ineligible,
        )
        return jsonify(eligibility_result), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except LookupError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return (
            jsonify({"error": "Failed to evaluate vessel eligibility", "details": str(error)}),
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
            status=EventStatus.CREATED.value,
            details=data.get("details", {}),
        )

        # Store DR event
        dynamoDB_client.put_item(item=drevent.to_dict())

        return jsonify(convert_decimals(drevent.to_dict())), 201

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

        return jsonify(convert_decimals(drevent.to_dict())), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to update DR event", "details": str(e)}),
            500,
        )


@drevents_bp.route("/<event_id>/cancel", methods=["PUT"])
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


@drevents_bp.route("/<event_id>/start", methods=["POST"])
@require_auth
@require_role("ADMIN")
def start_drevent(event_id):
    """Start dispatching a DR event"""
    try:

        item = dynamoDB_client.get_item(key={"id": event_id})
        if not item:
            return jsonify({"error": "DR event not found"}), 404

        drevent = DREvent.from_dict(item)

        if drevent.status == EventStatus.CANCELLED.value:
            return jsonify({"error": "Cannot start a cancelled event"}), 400

        contracts_client = DynamoClient(table_name="aquacharge-contracts-dev", region_name="us-east-1")
        valid_contracts = contracts_client.scan_items()
        valid_contracts = [c for c in valid_contracts if c.get("stationId") == drevent.stationId]

        if not valid_contracts:
            return jsonify({"error": "No valid contracts found for this event"}), 404

        _dispatch_loop(event_id, valid_contracts, dynamoDB_client)

        return jsonify({"message": f"Dispatch completed for event {event_id}"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to start DR event", "details": str(e)}), 500
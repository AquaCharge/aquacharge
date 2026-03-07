from flask import Blueprint, jsonify, request

from middleware.auth import require_auth, require_role
from services.contracts import ContractService
from services.drevents import DREventService, DREventServiceError
from services.eligibility import EligibilityService
from services.dr.dispatcher import _dispatch_loop
from models.drevent import DREvent, EventStatus
from db.dynamoClient import DynamoClient
from decimal import Decimal

drevents_bp = Blueprint("drevents", __name__)

contract_service = ContractService()
drevent_service = DREventService()
eligibility_service = EligibilityService()


dynamoDB_client = DynamoClient(table_name="aquacharge-drevents-dev", region_name="us-east-1")


@drevents_bp.route("", methods=["GET"])
@require_auth
def get_drevents():
    """Get all DR events, optionally filtered by status."""
    try:
        status_filter = request.args.get("status")
        return jsonify(drevent_service.list_events(status_filter=status_filter)), 200
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to retrieve DR events", "details": str(error)}),
            500,
        )


@drevents_bp.route("/monitoring", methods=["GET"])
@require_auth
def get_drevent_monitoring():
    """Get monitoring metrics for DR events."""
    try:
        snapshot = drevent_service.get_monitoring_snapshot(
            event_id=request.args.get("eventId"),
            region=request.args.get("region"),
            period_hours=request.args.get("periodHours", default=24, type=int),
        )
        return jsonify(snapshot), 200
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify(
                {
                    "error": "Failed to retrieve monitoring snapshot",
                    "details": str(error),
                }
            ),
            500,
        )


@drevents_bp.route("/<event_id>", methods=["GET"])
@require_auth
def get_drevent_by_id(event_id):
    """Get a specific DR event by ID."""
    try:
        return jsonify(drevent_service.get_event(event_id)), 200
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to retrieve DR event", "details": str(error)}),
            500,
        )


@drevents_bp.route("/<event_id>/eligibility", methods=["GET"])
@require_auth
def get_drevent_eligibility(event_id):
    """Evaluate vessel eligibility for a specific DR event."""
    try:
        event = drevent_service.get_event(event_id)
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
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify(
                {
                    "error": "Failed to evaluate vessel eligibility",
                    "details": str(error),
                }
            ),
            500,
        )


@drevents_bp.route("", methods=["POST"])
@require_auth
@require_role("ADMIN")
def create_drevent():
    """Create a new DR event."""
    try:
        return jsonify(drevent_service.create_event(request.get_json() or {})), 201
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to create DR event", "details": str(error)}),
            500,
        )


@drevents_bp.route("/<event_id>/dispatch", methods=["POST"])
@require_auth
def dispatch_drevent(event_id):
    """Dispatch a DR event: generate contracts for eligible vessels and advance state to Dispatched."""
    try:
        caller = request.current_user or {}
        if caller.get("type_name") != "POWER_OPERATOR":
            return jsonify({"error": "Only power operators can dispatch DR events"}), 403

        caller_user_id = str(caller.get("user_id") or caller.get("id") or "system")

        event = drevent_service.get_event(event_id)

        eligibility_result = eligibility_service.evaluate_vessels_for_event(
            event, include_ineligible=False
        )
        eligible_vessels = eligibility_result.get("vessels", [])

        created_contracts = contract_service.dispatch_event(
            dr_event=event,
            eligible_vessels=eligible_vessels,
            caller_user_id=caller_user_id,
        )

        updated_event = drevent_service.update_event(event_id, {"status": "Dispatched"})

        return jsonify({
            "message": "DR event dispatched successfully",
            "event": updated_event,
            "contractsCreated": len(created_contracts),
        }), 200

    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except LookupError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return jsonify({"error": "Failed to dispatch DR event", "details": str(error)}), 500


@drevents_bp.route("/<event_id>/cancel", methods=["PUT"])
@require_auth
def update_drevent(event_id):
    """Update an existing DR event with lifecycle guards."""
    try:
        return jsonify(drevent_service.update_event(event_id, request.get_json() or {})), 200
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to update DR event", "details": str(error)}),
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
        valid_contracts = [c for c in valid_contracts if c.get("drEventId") == drevent.id]

        if not valid_contracts:
            return jsonify({"error": "No valid contracts found for this event"}), 404

        _dispatch_loop(event_id, valid_contracts, dynamoDB_client)

        return jsonify({"message": f"Dispatch completed for event {event_id}"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to start DR event", "details": str(e)}), 500

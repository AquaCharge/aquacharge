from flask import Blueprint, jsonify, request

from middleware.auth import require_auth, require_role
from services.drevents import DREventService, DREventServiceError
from services.eligibility import EligibilityService

drevents_bp = Blueprint("drevents", __name__)

drevent_service = DREventService()
eligibility_service = EligibilityService()


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


@drevents_bp.route("/<event_id>", methods=["PUT"])
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

from flask import Blueprint, jsonify, request
from threading import Event, Lock, Thread

from middleware.auth import require_auth, require_user_type
from services.bookings import BookingService, BookingServiceError
from services.contracts import ContractService
from services.drevents import DREventService, DREventServiceError
from services.eligibility import EligibilityService
from services.dr.dispatcher import _dispatch_loop
from models.drevent import EventStatus
from models.user import UserType
from db.dynamoClient import DynamoClient
import config

drevents_bp = Blueprint("drevents", __name__)

contract_service = ContractService()
drevent_service = DREventService()
eligibility_service = EligibilityService()
booking_service = BookingService()
_dispatch_lock = Lock()
_running_dispatch_event_ids: set[str] = set()
_dispatch_stop_signals: dict[str, Event] = {}


def _mark_dispatch_running(event_id: str) -> Event | None:
    with _dispatch_lock:
        if event_id in _running_dispatch_event_ids:
            return None
        _running_dispatch_event_ids.add(event_id)
        stop_signal = Event()
        _dispatch_stop_signals[event_id] = stop_signal
        return stop_signal


def _request_dispatch_stop(event_id: str) -> bool:
    with _dispatch_lock:
        stop_signal = _dispatch_stop_signals.get(event_id)
        if not stop_signal:
            return False
        stop_signal.set()
        return True


def _clear_dispatch_running(event_id: str) -> None:
    with _dispatch_lock:
        _running_dispatch_event_ids.discard(event_id)
        _dispatch_stop_signals.pop(event_id, None)


def _complete_event_if_still_active(
    event_id: str, event_client: DynamoClient
) -> None:
    event = event_client.get_item(key={"id": event_id}) or {}
    if str(event.get("status") or "") != EventStatus.ACTIVE.value:
        return

    event_client.update_item(
        key={"id": event_id},
        update_data={"status": EventStatus.COMPLETED.value},
    )


def _dispatch_event_runner(
    event_id: str,
    valid_contracts: list[dict],
    event_client: DynamoClient,
    stop_signal: Event,
) -> None:
    try:
        _dispatch_loop(
            event_id,
            valid_contracts,
            event_client,
            stop_signal=stop_signal,
        )
        _complete_event_if_still_active(event_id, event_client)
    finally:
        _clear_dispatch_running(event_id)


def _start_dispatch_loop_async(
    event_id: str, valid_contracts: list[dict], stop_signal: Event
):
    event_client = DynamoClient(
        table_name=config.DREVENTS_TABLE, region_name=config.AWS_REGION
    )
    if config.DR_START_ASYNC:
        thread = Thread(
            target=_dispatch_event_runner,
            args=(event_id, valid_contracts, event_client, stop_signal),
            daemon=True,
            name=f"dr-dispatch-{event_id}",
        )
        thread.start()
        return thread

    _dispatch_event_runner(event_id, valid_contracts, event_client, stop_signal)
    return None


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


@drevents_bp.route("/analytics", methods=["GET"])
@require_auth
def get_drevent_analytics():
    """Get historical analytics metrics for DR events."""
    try:
        snapshot = drevent_service.get_analytics_snapshot(
            event_id=request.args.get("eventId"),
            region=request.args.get("region"),
            period_hours=request.args.get("periodHours", default=168, type=int),
            grain=request.args.get("grain", default="day", type=str),
        )
        return jsonify(snapshot), 200
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify(
                {
                    "error": "Failed to retrieve analytics snapshot",
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
@require_user_type(UserType.POWER_OPERATOR, "Only power operators can create DR events")
def create_drevent():
    """Create a new DR event."""
    try:
        payload = request.get_json() or {}
        station_id = str(payload.get("stationId") or "")
        if not station_id:
            return jsonify({"error": "stationId is required"}), 400

        station = drevent_service.station_repository.get_station(station_id)
        if not station:
            return jsonify({"error": "Station not found"}), 404

        availability = booking_service.get_station_availability(
            station_id=station_id,
            start_time_raw=str(payload.get("startTime") or ""),
            end_time_raw=str(payload.get("endTime") or ""),
        )
        if not any(charger.get("available") for charger in availability["chargers"]):
            return (
                jsonify(
                    {
                        "error": "Station has no available chargers for the requested window"
                    }
                ),
                400,
            )

        return jsonify(drevent_service.create_event(payload)), 201
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to create DR event", "details": str(error)}),
            500,
        )


@drevents_bp.route("/<event_id>/dispatch", methods=["POST"])
@require_auth
@require_user_type(UserType.POWER_OPERATOR, "Only power operators can dispatch DR events")
def dispatch_drevent(event_id):
    """Dispatch a DR event: generate contracts for eligible vessels and advance state to Dispatched."""
    try:
        caller = request.current_user or {}
        caller_user_id = str(caller.get("user_id") or caller.get("id") or "system")

        event = drevent_service.get_event(event_id)
        event_status = str(event.get("status") or "")
        if event_status not in {EventStatus.CREATED.value, EventStatus.DISPATCHED.value}:
            return (
                jsonify(
                    {
                        "error": (
                            "Only created or already dispatched DR events can generate "
                            "contract offers"
                        )
                    }
                ),
                400,
            )

        eligibility_result = eligibility_service.evaluate_vessels_for_event(
            event, include_ineligible=False
        )
        eligible_vessels = eligibility_result.get("vessels", [])
        considered_vessels = eligible_vessels

        created_contracts = contract_service.dispatch_event(
            dr_event=event,
            eligible_vessels=eligible_vessels,
            caller_user_id=caller_user_id,
        )

        updated_event = event
        if event_status == EventStatus.CREATED.value:
            updated_event = drevent_service.update_event(event_id, {"status": "Dispatched"})

        contracts_skipped = max(0, len(considered_vessels) - len(created_contracts))
        return (
            jsonify(
                {
                    "message": "DR event dispatched successfully",
                    "event": updated_event,
                    "eligibleVessels": len(eligible_vessels),
                    "contractsCreated": len(created_contracts),
                    "contractsSkipped": contracts_skipped,
                }
            ),
            200,
        )

    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except LookupError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return (
            jsonify({"error": "Failed to dispatch DR event", "details": str(error)}),
            500,
        )


@drevents_bp.route("/<event_id>/cancel", methods=["PUT"])
@require_auth
def update_drevent(event_id):
    """Update an existing DR event with lifecycle guards."""
    try:
        return (
            jsonify(drevent_service.update_event(event_id, request.get_json() or {})),
            200,
        )
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify({"error": "Failed to update DR event", "details": str(error)}),
            500,
        )


@drevents_bp.route("/<event_id>/start", methods=["POST"])
@require_auth
@require_user_type(UserType.POWER_OPERATOR, "Only power operators can start DR events")
def start_drevent(event_id):
    """Start dispatching a DR event"""
    try:
        event = drevent_service.get_event(event_id)
        if str(event.get("status") or "") != EventStatus.COMMITTED.value:
            return jsonify({"error": "Only committed DR events can be started"}), 400

        contracts_client = DynamoClient(
            table_name=config.CONTRACTS_TABLE, region_name=config.AWS_REGION
        )
        valid_contracts = [
            contract
            for contract in contracts_client.scan_items()
            if str(contract.get("drEventId") or "") == event_id
            and str(contract.get("status") or "").lower() == "active"
            and bool(str(contract.get("bookingId") or "").strip())
        ]

        if not valid_contracts:
            return (
                jsonify({"error": "No booked active contracts found for this event"}),
                400,
            )

        stop_signal = _mark_dispatch_running(event_id)
        if not stop_signal:
            return jsonify({"error": "DR event is already running"}), 409

        drevent_service.update_event(event_id, {"status": EventStatus.ACTIVE.value})

        try:
            _start_dispatch_loop_async(event_id, valid_contracts, stop_signal)
        except Exception:
            _clear_dispatch_running(event_id)
            try:
                drevent_service.update_event(
                    event_id, {"status": EventStatus.COMMITTED.value}
                )
            except Exception:
                pass
            raise

        return (
            jsonify(
                {
                    "message": f"Dispatch started for event {event_id}",
                    "eventId": event_id,
                    "status": EventStatus.ACTIVE.value,
                    "contractsStarted": len(valid_contracts),
                    "async": bool(config.DR_START_ASYNC),
                }
            ),
            202,
        )

    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to start DR event", "details": str(e)}), 500


@drevents_bp.route("/<event_id>/end", methods=["POST"])
@require_auth
@require_user_type(UserType.POWER_OPERATOR, "Only power operators can end DR events")
def end_drevent(event_id):
    """End an active DR event and stop its live dispatch loop."""
    try:
        event = drevent_service.get_event(event_id)
        if str(event.get("status") or "") != EventStatus.ACTIVE.value:
            return jsonify({"error": "Only active DR events can be ended"}), 400

        dispatch_stopped = _request_dispatch_stop(event_id)
        drevent_service.update_event(event_id, {"status": EventStatus.COMPLETED.value})

        return (
            jsonify(
                {
                    "message": f"DR event {event_id} ended successfully",
                    "eventId": event_id,
                    "status": EventStatus.COMPLETED.value,
                    "dispatchStopped": dispatch_stopped,
                }
            ),
            200,
        )
    except DREventServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return jsonify({"error": "Failed to end DR event", "details": str(error)}), 500

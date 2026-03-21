from flask import Blueprint, jsonify, request
from boto3.dynamodb.conditions import Key
from db.dynamoClient import DynamoClient
from middleware.auth import require_auth, require_role, require_user_type
from models.user import UserType
from services.bookings import BookingService, BookingServiceError
from services.contracts import ContractService, ContractServiceError, convert_decimals
from services.eligibility import EligibilityService
import config

_vessels_client = DynamoClient(
    table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
)

contracts_bp = Blueprint("contracts", __name__)
contract_service = ContractService()
eligibility_service = EligibilityService()
booking_service = BookingService()


def _get_current_user_id():
    caller = request.current_user or {}
    user_id = caller.get("user_id") or caller.get("id")
    return None if user_id is None else str(user_id)


def _get_current_vessel_id():
    caller = request.current_user or {}
    vessel_id = caller.get("currentVesselId")
    return None if vessel_id is None else str(vessel_id)


def _get_owned_vessel_ids(user_id: str):
    try:
        vessels = _vessels_client.query_gsi(
            index_name="userId-index",
            key_condition_expression=Key("userId").eq(user_id),
        )
    except Exception:
        try:
            vessels = [
                vessel
                for vessel in _vessels_client.scan_items()
                if str(vessel.get("userId") or "") == user_id
            ]
        except Exception:
            vessels = []
    return [v["id"] for v in vessels] if vessels else []


def _get_current_eligibility(contract):
    dr_event = contract_service.drevent_repository.get_event(contract.get("drEventId"))
    if not dr_event:
        return None

    try:
        eligibility_result = eligibility_service.evaluate_vessels_for_event(
            dr_event,
            include_ineligible=True,
        )
    except Exception:
        return None
    for vessel_result in eligibility_result.get("vessels", []):
        if vessel_result.get("vesselId") == contract.get("vesselId"):
            return vessel_result
    return None


def _resolve_caller_vessel_ids() -> list[str]:
    user_id = _get_current_user_id()
    if user_id is None:
        return []

    vessel_ids = _get_owned_vessel_ids(user_id)
    current_vessel_id = _get_current_vessel_id()
    if current_vessel_id and current_vessel_id not in vessel_ids:
        vessel_ids.append(current_vessel_id)
    return vessel_ids


def _build_booking_context(contract: dict) -> dict:
    dr_event = contract_service.drevent_repository.get_event(contract.get("drEventId")) or {}

    try:
        booking_context = booking_service.get_station_availability(
            station_id=str(dr_event.get("stationId") or ""),
            start_time_raw=str(contract.get("startTime") or ""),
            end_time_raw=str(contract.get("endTime") or ""),
        )
        return {
            "stationId": booking_context["stationId"],
            "startTime": booking_context["startTime"],
            "endTime": booking_context["endTime"],
            "availableSlots": booking_context["chargers"],
        }
    except Exception as error:
        return {
            "stationId": str(dr_event.get("stationId") or ""),
            "startTime": str(contract.get("startTime") or ""),
            "endTime": str(contract.get("endTime") or ""),
            "availableSlots": [],
            "warning": f"Availability lookup failed: {error}",
        }


@contracts_bp.route("", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        status_filter = request.args.get("status")
        vessel_id = request.args.get("vesselId")
        filtered_contracts = contract_service.list_contracts(
            status_filter=status_filter,
            vessel_id=vessel_id,
        )

        return jsonify(convert_decimals(filtered_contracts)), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve contracts", "details": str(e)}),
            500,
        )


@contracts_bp.route("/<contract_id>", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contract(contract_id: str):
    """Get a specific contract by ID"""
    try:
        contract = contract_service.get_contract(contract_id)
        return jsonify(convert_decimals(contract)), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to retrieve contract", "details": str(e)}), 500


@contracts_bp.route("", methods=["POST"])
@require_auth
@require_role("ADMIN")
def create_contract():
    """Create a new contract"""
    try:
        data = request.get_json()
        contract = contract_service.create_contract(data)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract created successfully",
                        "contract": contract,
                    }
                )
            ),
            201,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to create contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["PUT"])
def update_contract(contract_id: str):
    """Update a contract"""
    try:
        data = request.get_json()
        contract = contract_service.update_contract(contract_id, data)
        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract updated successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to update contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/cancel", methods=["POST"])
def cancel_contract(contract_id: str):
    """Cancel a pending contract"""
    try:
        contract = contract_service.cancel_contract(contract_id)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract cancelled successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to cancel contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/complete", methods=["POST"])
def complete_contract(contract_id: str):
    """Mark a contract as completed"""
    try:
        contract = contract_service.complete_contract(contract_id)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract completed successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to complete contract", "details": str(e)}), 500


@contracts_bp.route("/my-contracts", methods=["GET"])
@require_auth
def get_my_contracts():
    """Get contracts for the authenticated vessel operator"""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        status_filter = request.args.get("status")

        vessel_ids = _get_owned_vessel_ids(user_id)
        current_vessel_id = _get_current_vessel_id()
        if current_vessel_id and current_vessel_id not in vessel_ids:
            vessel_ids.append(current_vessel_id)

        all_contracts = []
        for vid in vessel_ids:
            try:
                vessel_contracts = contract_service.list_contracts(
                    status_filter=status_filter,
                    vessel_id=vid,
                )
            except Exception:
                continue
            all_contracts.extend(vessel_contracts)

        visible_contracts = []
        for contract in all_contracts:
            if contract.get("status") != "pending":
                visible_contracts.append(contract)
                continue

            eligibility = _get_current_eligibility(contract)
            if eligibility and not eligibility.get("eligible"):
                continue

            contract_with_eligibility = dict(contract)
            if eligibility:
                contract_with_eligibility["eligibility"] = eligibility
            visible_contracts.append(contract_with_eligibility)

        visible_contracts.sort(key=lambda c: str(c.get("createdAt") or ""), reverse=True)
        return jsonify(convert_decimals(visible_contracts)), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve contracts", "details": str(e)}),
            500,
        )


@contracts_bp.route("/<contract_id>/accept", methods=["POST"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can accept contracts")
def accept_contract(contract_id: str):
    """Accept a pending contract (vessel operator only)"""
    try:
        if _get_current_user_id() is None:
            return jsonify({"error": "Authentication required"}), 401
        vessel_ids = _resolve_caller_vessel_ids()

        contract_snapshot = contract_service.get_contract(contract_id)
        eligibility = _get_current_eligibility(contract_snapshot)
        if contract_snapshot.get("status") == "pending" and eligibility and (
            not eligibility.get("eligible")
        ):
            reasons = eligibility.get("reasons") if eligibility else None
            reason_text = ", ".join(reasons) if reasons else "Vessel is no longer eligible"
            return jsonify({"error": reason_text}), 409

        contract = contract_service.accept_contract(
            contract_id,
            vessel_ids,
            request.get_json(silent=True) or {},
        )
        booking_context = _build_booking_context(contract)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract accepted successfully",
                        "contract": contract,
                        "bookingContext": booking_context,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to accept contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/booking-context", methods=["GET"])
@require_auth
@require_user_type(
    UserType.VESSEL_OPERATOR,
    "Only vessel operators can resume contract booking",
)
def get_contract_booking_context(contract_id: str):
    """Return live booking context for an accepted contract awaiting charger selection."""
    try:
        if _get_current_user_id() is None:
            return jsonify({"error": "Authentication required"}), 401

        vessel_ids = _resolve_caller_vessel_ids()
        contract = contract_service.get_contract(contract_id)

        if contract.get("vesselId") not in vessel_ids:
            return jsonify({"error": "You do not own the vessel on this contract"}), 403

        if contract.get("bookingId"):
            return jsonify({"error": "This contract already has a booking"}), 409

        booking_context = _build_booking_context(contract)
        return (
            jsonify(
                convert_decimals(
                    {
                        "contract": contract,
                        "bookingContext": booking_context,
                    }
                )
            ),
            200,
        )
    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as error:
        return (
            jsonify(
                {
                    "error": "Failed to load contract booking context",
                    "details": str(error),
                }
            ),
            500,
        )


@contracts_bp.route("/<contract_id>/decline", methods=["POST"])
@require_auth
def decline_contract(contract_id: str):
    """Decline a pending contract (vessel operator only)"""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        vessel_ids = _get_owned_vessel_ids(user_id)

        contract = contract_service.decline_contract(contract_id, vessel_ids)
        return (
            jsonify(
                convert_decimals(
                    {"message": "Contract declined successfully", "contract": contract}
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to decline contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["DELETE"])
def delete_contract(contract_id: str):
    """Delete a contract (admin only)"""
    try:
        contract_service.delete_contract(contract_id)

        return jsonify({"message": "Contract deleted successfully"}), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to delete contract", "details": str(e)}), 500

from boto3.dynamodb.conditions import Key
from flask import Blueprint, jsonify, request
import config
from db.dynamoClient import DynamoClient
from middleware.auth import require_auth, require_user_type
from models.user import UserType
from services.bookings import BookingService, BookingServiceError

bookings_bp = Blueprint("bookings", __name__)
booking_service = BookingService()
_vessels_client = DynamoClient(
    table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
)


def _get_current_user_id():
    caller = request.current_user or {}
    user_id = caller.get("user_id") or caller.get("id")
    return None if user_id is None else str(user_id)


def _get_owned_vessel_ids(user_id: str):
    try:
        vessels = _vessels_client.query_gsi(
            index_name="userId-index",
            key_condition_expression=Key("userId").eq(user_id),
        )
    except Exception:
        vessels = [
            vessel
            for vessel in _vessels_client.scan_items()
            if str(vessel.get("userId") or "") == user_id
        ]
    return [str(vessel["id"]) for vessel in vessels] if vessels else []


@bookings_bp.route("", methods=["GET"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can access bookings")
def get_bookings():
    """Get bookings for the authenticated vessel operator."""
    user_id = _get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required"}), 401
    status = request.args.get("status")
    try:
        bookings = booking_service.list_bookings(user_id=user_id, status=status)
        return jsonify(bookings), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["GET"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can access bookings")
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        booking = booking_service.get_booking(booking_id, user_id=user_id)
        return jsonify(booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("", methods=["POST"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can create bookings")
def create_booking():
    """Create a new booking"""
    data = request.get_json() or {}
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401

        vessel_id = str(data.get("vesselId") or "")
        if vessel_id not in _get_owned_vessel_ids(user_id):
            return jsonify({"error": "You do not own the selected vessel"}), 403

        data["userId"] = user_id
        booking = booking_service.create_booking(data)
        return jsonify(booking), 201
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["PUT"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can update bookings")
def update_booking(booking_id: str):
    """Update an existing booking"""
    data = request.get_json() or {}
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        updated_booking = booking_service.update_booking(
            booking_id,
            data,
            user_id=user_id,
        )
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can cancel bookings")
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        updated_booking = booking_service.cancel_booking(booking_id, user_id=user_id)
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can cancel bookings")
def delete_booking(booking_id: str):
    """Cancel a booking using the DELETE contract."""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        booking = booking_service.delete_booking(booking_id, user_id=user_id)
        return jsonify(booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/upcoming", methods=["GET"])
@require_auth
@require_user_type(UserType.VESSEL_OPERATOR, "Only vessel operators can access bookings")
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    try:
        user_id = _get_current_user_id()
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        upcoming = booking_service.list_upcoming_bookings(user_id)
        return jsonify(upcoming), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code

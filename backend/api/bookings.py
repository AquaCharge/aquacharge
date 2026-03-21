from boto3.dynamodb.conditions import Key
from flask import Blueprint, jsonify, request
import config
from db.dynamoClient import DynamoClient
from middleware.auth import decode_jwt_token
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


def _load_optional_user():
    auth_header = request.headers.get("Authorization")
    request.current_user = None
    if not auth_header:
        return None
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401

    token = auth_header.split(" ", 1)[1]
    try:
        request.current_user = decode_jwt_token(token)
    except ValueError as error:
        return jsonify({"error": str(error)}), 401
    except Exception:
        return jsonify({"error": "Authentication failed"}), 401
    return None


def _get_current_user_type():
    caller = request.current_user or {}
    user_type = caller.get("type")
    if user_type is None:
        return None
    try:
        return UserType(user_type)
    except ValueError:
        return None


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
def get_bookings():
    """Get bookings, optionally scoped to the authenticated vessel operator."""
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error

    status = request.args.get("status")
    user_id = None
    current_type = _get_current_user_type()
    if current_type == UserType.VESSEL_OPERATOR:
        user_id = _get_current_user_id()
    elif current_type is None:
        user_id = request.args.get("userId")

    try:
        bookings = booking_service.list_bookings(user_id=user_id, status=status)
        return jsonify(bookings), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        if _get_current_user_type() != UserType.VESSEL_OPERATOR:
            user_id = None
        booking = booking_service.get_booking(booking_id, user_id=user_id)
        return jsonify(booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("", methods=["POST"])
def create_booking():
    """Create a new booking"""
    data = request.get_json() or {}
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        current_type = _get_current_user_type()
        if user_id is not None:
            if current_type != UserType.VESSEL_OPERATOR:
                return jsonify({"error": "Only vessel operators can create bookings"}), 403

            vessel_id = str(data.get("vesselId") or "")
            if vessel_id not in _get_owned_vessel_ids(user_id):
                return jsonify({"error": "You do not own the selected vessel"}), 403

            data["userId"] = user_id

        booking = booking_service.create_booking(data)
        return jsonify(booking), 201
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id: str):
    """Update an existing booking"""
    data = request.get_json() or {}
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        current_type = _get_current_user_type()
        if user_id is not None and current_type != UserType.VESSEL_OPERATOR:
            return jsonify({"error": "Only vessel operators can update bookings"}), 403
        if current_type != UserType.VESSEL_OPERATOR:
            user_id = None
        updated_booking = booking_service.update_booking(
            booking_id,
            data,
            user_id=user_id,
        )
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        current_type = _get_current_user_type()
        if user_id is not None and current_type != UserType.VESSEL_OPERATOR:
            return jsonify({"error": "Only vessel operators can cancel bookings"}), 403
        if current_type != UserType.VESSEL_OPERATOR:
            user_id = None
        updated_booking = booking_service.cancel_booking(booking_id, user_id=user_id)
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id: str):
    """Cancel a booking using the DELETE contract."""
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        current_type = _get_current_user_type()
        if user_id is not None and current_type != UserType.VESSEL_OPERATOR:
            return jsonify({"error": "Only vessel operators can cancel bookings"}), 403
        if current_type != UserType.VESSEL_OPERATOR:
            user_id = None
        booking = booking_service.delete_booking(booking_id, user_id=user_id)
        return jsonify(booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/upcoming", methods=["GET"])
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    auth_error = _load_optional_user()
    if auth_error:
        return auth_error
    try:
        user_id = _get_current_user_id()
        if _get_current_user_type() != UserType.VESSEL_OPERATOR:
            user_id = request.args.get("userId")
        upcoming = booking_service.list_upcoming_bookings(user_id)
        return jsonify(upcoming), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code

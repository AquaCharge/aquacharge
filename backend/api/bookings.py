from flask import Blueprint, jsonify, request
from services.bookings import BookingService, BookingServiceError

bookings_bp = Blueprint("bookings", __name__)
booking_service = BookingService()


@bookings_bp.route("", methods=["GET"])
def get_bookings():
    """Get all bookings, optionally filtered by user or status"""
    user_id = request.args.get("userId")
    status = request.args.get("status")
    try:
        bookings = booking_service.list_bookings(user_id=user_id, status=status)
        return jsonify(bookings), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    try:
        booking = booking_service.get_booking(booking_id)
        return jsonify(booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("", methods=["POST"])
def create_booking():
    """Create a new booking"""
    data = request.get_json()
    try:
        booking = booking_service.create_booking(data)
        return jsonify(booking), 201
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id: str):
    """Update an existing booking"""
    data = request.get_json()
    try:
        updated_booking = booking_service.update_booking(booking_id, data)
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    try:
        updated_booking = booking_service.cancel_booking(booking_id)
        return jsonify(updated_booking), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id: str):
    """Delete a booking"""
    try:
        booking_service.delete_booking(booking_id)
        return jsonify({"message": "Booking deleted successfully"}), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@bookings_bp.route("/upcoming", methods=["GET"])
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    user_id = request.args.get("userId")
    try:
        upcoming = booking_service.list_upcoming_bookings(user_id)
        return jsonify(upcoming), 200
    except BookingServiceError as error:
        return jsonify({"error": error.message}), error.status_code

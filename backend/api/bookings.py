from flask import Blueprint, jsonify, request
from models.booking import Booking, BookingStatus
from datetime import datetime, timezone
from db.dynamoClient import DynamoClient

bookings_bp = Blueprint("bookings", __name__)

dynamoDB_client = DynamoClient(
    table_name="aquacharge-bookings-dev", region_name="us-east-1"
)


def parse_datetime_safe(dt_string):
    """Parse datetime string and ensure it's timezone-aware (UTC)"""
    dt = datetime.fromisoformat(dt_string)
    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc():
    """Get current datetime in UTC"""
    return datetime.now(timezone.utc)


@bookings_bp.route("", methods=["GET"])
def get_bookings():
    """Get all bookings, optionally filtered by user or status"""
    user_id = request.args.get("userId")
    status = request.args.get("status")

    bookings = dynamoDB_client.scan_items()

    if user_id:
        bookings = [b for b in bookings if b.get("userId") == user_id]

    if status:
        try:
            status_enum = BookingStatus[status.upper()]
            bookings = [b for b in bookings if b.get("status") == status_enum.value]
        except KeyError:
            return jsonify({"error": "Invalid status"}), 400

    return jsonify(bookings), 200


@bookings_bp.route("/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    booking = dynamoDB_client.get_item(key={"id": booking_id})

    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify(booking), 200


@bookings_bp.route("", methods=["POST"])
def create_booking():
    """Create a new booking"""
    data = request.get_json()

    # Validate required fields
    required_fields = [
        "userId",
        "vesselId",
        "stationId",
        "startTime",
        "endTime",
        "chargerType",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Parse datetime strings
    try:
        start_time = parse_datetime_safe(data["startTime"])
        end_time = parse_datetime_safe(data["endTime"])
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Use ISO format."}), 400

    # Validate time range
    if end_time <= start_time:
        return jsonify({"error": "End time must be after start time"}), 400

    # Check for conflicts (simplified - would need proper DB queries)
    bookings = dynamoDB_client.scan_items()
    for booking_dict in bookings:
        if booking_dict.get("stationId") == data["stationId"] and booking_dict.get(
            "status"
        ) in [
            BookingStatus.PENDING.value,
            BookingStatus.CONFIRMED.value,
        ]:
            # Check for time overlap
            booking_start = parse_datetime_safe(booking_dict["startTime"])
            booking_end = parse_datetime_safe(booking_dict["endTime"])
            if not (end_time <= booking_start or start_time >= booking_end):
                return (
                    jsonify({"error": "Time slot conflicts with existing booking"}),
                    409,
                )

    # Create booking instance
    booking = Booking(
        userId=data["userId"],
        vesselId=data["vesselId"],
        stationId=data["stationId"],
        startTime=start_time,
        endTime=end_time,
        chargerType=data["chargerType"],
        status=(
            BookingStatus[data.get("status", "PENDING").upper()]
            if "status" in data
            else BookingStatus.PENDING
        ),
    )

    # Store booking
    dynamoDB_client.put_item(booking.to_dict())

    return jsonify(booking.to_dict()), 201


@bookings_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id: str):
    """Update an existing booking"""
    booking_dict = dynamoDB_client.get_item(key={"id": booking_id})
    if not booking_dict:
        return jsonify({"error": "Booking not found"}), 404

    data = request.get_json()
    update_data = {}

    # Update status
    if "status" in data:
        try:
            status_enum = BookingStatus[data["status"].upper()]
            update_data["status"] = status_enum.value
        except KeyError:
            return jsonify({"error": "Invalid status"}), 400

    # Update times if provided
    start_time = parse_datetime_safe(booking_dict["startTime"])
    end_time = parse_datetime_safe(booking_dict["endTime"])

    if "startTime" in data:
        start_time = parse_datetime_safe(data["startTime"])
        update_data["startTime"] = start_time.isoformat()
    if "endTime" in data:
        end_time = parse_datetime_safe(data["endTime"])
        update_data["endTime"] = end_time.isoformat()

    # Validate time range
    if end_time <= start_time:
        return jsonify({"error": "End time must be after start time"}), 400

    updated_booking = dynamoDB_client.update_item(
        key={"id": booking_id}, update_data=update_data
    )

    return jsonify(updated_booking), 200


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    booking_dict = dynamoDB_client.get_item(key={"id": booking_id})
    if not booking_dict:
        return jsonify({"error": "Booking not found"}), 404

    if booking_dict.get("status") == BookingStatus.COMPLETED.value:
        return jsonify({"error": "Cannot cancel completed booking"}), 400

    updated_booking = dynamoDB_client.update_item(
        key={"id": booking_id}, update_data={"status": BookingStatus.CANCELLED.value}
    )

    return jsonify(updated_booking), 200


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id: str):
    """Delete a booking"""
    booking = dynamoDB_client.get_item(key={"id": booking_id})
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    dynamoDB_client.delete_item(key={"id": booking_id})
    return jsonify({"message": "Booking deleted successfully"}), 200


@bookings_bp.route("/upcoming", methods=["GET"])
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"error": "userId parameter is required"}), 400

    bookings = dynamoDB_client.scan_items()
    current_time = now_utc()

    upcoming = []
    for booking_dict in bookings:
        booking_start = parse_datetime_safe(booking_dict["startTime"])
        if (
            booking_dict.get("userId") == user_id
            and booking_start > current_time
            and booking_dict.get("status")
            in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]
        ):
            upcoming.append(booking_dict)

    # Sort by start time
    upcoming.sort(key=lambda x: x["startTime"])

    return jsonify(upcoming), 200

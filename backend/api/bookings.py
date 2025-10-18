from flask import Blueprint, jsonify, request
from models.booking import Booking, BookingStatus
from datetime import datetime, timedelta
from typing import Dict

bookings_bp = Blueprint("bookings", __name__)

# In-memory storage (replace with actual database)
bookings_db: Dict[str, Booking] = {}


# Initialize with sample data
def init_sample_bookings():
    if not bookings_db:  # Only initialize if empty
        base_time = datetime(2024, 10, 18, 8, 0, 0)  # Starting from today

        sample_bookings = [
            # Completed bookings
            Booking(
                id="booking-001",
                userId="user-003",
                vesselId="vessel-001",
                stationId="station-001",
                startTime=base_time - timedelta(days=5, hours=2),
                endTime=base_time - timedelta(days=5),
                status=BookingStatus.COMPLETED,
                chargerType="Type 2 AC",
                createdAt=base_time - timedelta(days=7),
            ),
            Booking(
                id="booking-002",
                userId="user-004",
                vesselId="vessel-003",
                stationId="station-002",
                startTime=base_time - timedelta(days=3, hours=3),
                endTime=base_time - timedelta(days=3, hours=1),
                status=BookingStatus.COMPLETED,
                chargerType="Type 2 AC",
                createdAt=base_time - timedelta(days=5),
            ),
            # Confirmed upcoming bookings
            Booking(
                id="booking-003",
                userId="user-003",
                vesselId="vessel-002",
                stationId="station-001",
                startTime=base_time + timedelta(hours=4),
                endTime=base_time + timedelta(hours=6),
                status=BookingStatus.CONFIRMED,
                chargerType="CCS DC",
                createdAt=base_time - timedelta(days=2),
            ),
            Booking(
                id="booking-004",
                userId="user-005",
                vesselId="vessel-005",
                stationId="station-004",
                startTime=base_time + timedelta(days=1, hours=6),
                endTime=base_time + timedelta(days=1, hours=8),
                status=BookingStatus.CONFIRMED,
                chargerType="CHAdeMO",
                createdAt=base_time - timedelta(days=1),
            ),
            # Pending bookings
            Booking(
                id="booking-005",
                userId="user-002",
                vesselId="vessel-006",
                stationId="station-001",
                startTime=base_time + timedelta(days=2, hours=10),
                endTime=base_time + timedelta(days=2, hours=12),
                status=BookingStatus.PENDING,
                chargerType="Type 2 AC",
                createdAt=base_time - timedelta(hours=6),
            ),
            Booking(
                id="booking-006",
                userId="user-004",
                vesselId="vessel-003",
                stationId="station-006",
                startTime=base_time + timedelta(days=3, hours=14),
                endTime=base_time + timedelta(days=3, hours=16),
                status=BookingStatus.PENDING,
                chargerType="Type 2 AC",
                createdAt=base_time - timedelta(hours=2),
            ),
            # Cancelled booking
            Booking(
                id="booking-007",
                userId="user-005",
                vesselId="vessel-004",
                stationId="station-003",
                startTime=base_time - timedelta(days=1, hours=10),
                endTime=base_time - timedelta(days=1, hours=8),
                status=BookingStatus.CANCELLED,
                chargerType="CCS DC",
                createdAt=base_time - timedelta(days=3),
            ),
            # More future bookings
            Booking(
                id="booking-008",
                userId="user-003",
                vesselId="vessel-001",
                stationId="station-002",
                startTime=base_time + timedelta(days=7, hours=9),
                endTime=base_time + timedelta(days=7, hours=11),
                status=BookingStatus.CONFIRMED,
                chargerType="Type 2 AC",
                createdAt=base_time - timedelta(hours=12),
            ),
        ]

        for booking in sample_bookings:
            bookings_db[booking.id] = booking


# Initialize sample data when module is imported
init_sample_bookings()


@bookings_bp.route("", methods=["GET"])
def get_bookings():
    """Get all bookings, optionally filtered by user or status"""
    user_id = request.args.get("userId")
    status = request.args.get("status")

    bookings = list(bookings_db.values())

    if user_id:
        bookings = [b for b in bookings if b.userId == user_id]

    if status:
        try:
            status_enum = BookingStatus[status.upper()]
            bookings = [b for b in bookings if b.status == status_enum]
        except KeyError:
            return jsonify({"error": "Invalid status"}), 400

    return jsonify([b.to_dict() for b in bookings]), 200


@bookings_bp.route("/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    if booking_id not in bookings_db:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify(bookings_db[booking_id].to_dict()), 200


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
        start_time = datetime.fromisoformat(data["startTime"])
        end_time = datetime.fromisoformat(data["endTime"])
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Use ISO format."}), 400

    # Validate time range
    if end_time <= start_time:
        return jsonify({"error": "End time must be after start time"}), 400

    # Check for conflicts (simplified - would need proper DB queries)
    for booking in bookings_db.values():
        if booking.stationId == data["stationId"] and booking.status in [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        ]:
            # Check for time overlap
            if not (end_time <= booking.startTime or start_time >= booking.endTime):
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
    bookings_db[booking.id] = booking

    return jsonify(booking.to_dict()), 201


@bookings_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id: str):
    """Update an existing booking"""
    if booking_id not in bookings_db:
        return jsonify({"error": "Booking not found"}), 404

    data = request.get_json()
    booking = bookings_db[booking_id]

    # Update status
    if "status" in data:
        try:
            booking.status = BookingStatus[data["status"].upper()]
        except KeyError:
            return jsonify({"error": "Invalid status"}), 400

    # Update times if provided
    if "startTime" in data:
        booking.startTime = datetime.fromisoformat(data["startTime"])
    if "endTime" in data:
        booking.endTime = datetime.fromisoformat(data["endTime"])

    # Validate time range
    if booking.endTime <= booking.startTime:
        return jsonify({"error": "End time must be after start time"}), 400

    return jsonify(booking.to_dict()), 200


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    if booking_id not in bookings_db:
        return jsonify({"error": "Booking not found"}), 404

    booking = bookings_db[booking_id]

    if booking.status == BookingStatus.COMPLETED:
        return jsonify({"error": "Cannot cancel completed booking"}), 400

    booking.status = BookingStatus.CANCELLED

    return jsonify(booking.to_dict()), 200


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id: str):
    """Delete a booking"""
    if booking_id not in bookings_db:
        return jsonify({"error": "Booking not found"}), 404

    del bookings_db[booking_id]
    return jsonify({"message": "Booking deleted successfully"}), 200


@bookings_bp.route("/upcoming", methods=["GET"])
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"error": "userId parameter is required"}), 400

    current_time = datetime.now()
    upcoming = [
        b.to_dict()
        for b in bookings_db.values()
        if b.userId == user_id
        and b.startTime > current_time
        and b.status in [BookingStatus.PENDING, BookingStatus.CONFIRMED]
    ]

    # Sort by start time
    upcoming.sort(key=lambda x: x["startTime"])

    return jsonify(upcoming), 200

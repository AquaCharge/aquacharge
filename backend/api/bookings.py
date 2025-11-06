from flask import Blueprint, jsonify, request
from models.booking import Booking, BookingStatus
from datetime import datetime
from db.dynamodb import db_client

bookings_bp = Blueprint("bookings", __name__)


@bookings_bp.route("", methods=["GET"])
def get_bookings():
    """Get all bookings, optionally filtered by user or status"""
    try:
        user_id = request.args.get("userId")
        status = request.args.get("status")

        if user_id:
            bookings_data = db_client.get_bookings_by_user(user_id)
        else:
            bookings_data = db_client.scan_table(
                db_client.bookings_table_name, limit=1000
            )

        bookings = [Booking.from_dict(b) for b in bookings_data]

        if status:
            try:
                status_enum = BookingStatus[status.upper()]
                bookings = [b for b in bookings if b.status == status_enum]
            except KeyError:
                return jsonify({"error": "Invalid status"}), 400

        return jsonify([b.to_dict() for b in bookings]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch bookings", "details": str(e)}), 500


@bookings_bp.route("/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    try:
        booking_data = db_client.get_booking_by_id(booking_id)

        if not booking_data:
            return jsonify({"error": "Booking not found"}), 404

        booking = Booking.from_dict(booking_data)
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch booking", "details": str(e)}), 500


@bookings_bp.route("", methods=["POST"])
def create_booking():
    """Create a new booking"""
    try:
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

        # Check for conflicts - query bookings at this station
        station_bookings = db_client.scan_table(
            db_client.bookings_table_name,
            filter_expression="stationId = :sid",
            expression_values={":sid": data["stationId"]},
            limit=1000,
        )

        for booking_data in station_bookings:
            booking = Booking.from_dict(booking_data)
            if booking.status in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
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

        # Store booking in DynamoDB
        db_client.create_booking(booking.to_dict())

        return jsonify(booking.to_dict()), 201
    except Exception as e:
        return jsonify({"error": "Failed to create booking", "details": str(e)}), 500


@bookings_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id: str):
    """Update an existing booking"""
    try:
        booking_data = db_client.get_booking_by_id(booking_id)

        if not booking_data:
            return jsonify({"error": "Booking not found"}), 404

        data = request.get_json()
        booking = Booking.from_dict(booking_data)

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

        # Update in DynamoDB
        db_client.put_item(db_client.bookings_table_name, booking.to_dict())

        return jsonify(booking.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to update booking", "details": str(e)}), 500


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id: str):
    """Cancel a booking"""
    try:
        booking_data = db_client.get_booking_by_id(booking_id)

        if not booking_data:
            return jsonify({"error": "Booking not found"}), 404

        booking = Booking.from_dict(booking_data)

        if booking.status == BookingStatus.COMPLETED:
            return jsonify({"error": "Cannot cancel completed booking"}), 400

        booking.status = BookingStatus.CANCELLED

        # Update in DynamoDB
        db_client.put_item(db_client.bookings_table_name, booking.to_dict())

        return jsonify(booking.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to cancel booking", "details": str(e)}), 500


@bookings_bp.route("/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id: str):
    """Delete a booking"""
    try:
        booking_data = db_client.get_booking_by_id(booking_id)

        if not booking_data:
            return jsonify({"error": "Booking not found"}), 404

        db_client.delete_item(db_client.bookings_table_name, {"id": booking_id})
        return jsonify({"message": "Booking deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete booking", "details": str(e)}), 500


@bookings_bp.route("/upcoming", methods=["GET"])
def get_upcoming_bookings():
    """Get upcoming bookings for a user"""
    try:
        user_id = request.args.get("userId")

        if not user_id:
            return jsonify({"error": "userId parameter is required"}), 400

        bookings_data = db_client.get_bookings_by_user(user_id)
        current_time = datetime.now()

        upcoming = [
            Booking.from_dict(b).to_dict()
            for b in bookings_data
            if datetime.fromisoformat(b["startTime"]) > current_time
            and BookingStatus[b["status"]]
            in [BookingStatus.PENDING, BookingStatus.CONFIRMED]
        ]

        # Sort by start time
        upcoming.sort(key=lambda x: x["startTime"])

        return jsonify(upcoming), 200
    except Exception as e:
        return (
            jsonify({"error": "Failed to fetch upcoming bookings", "details": str(e)}),
            500,
        )

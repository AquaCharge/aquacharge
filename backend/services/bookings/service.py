from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from db.dynamoClient import DynamoClient
from models.booking import Booking, BookingStatus


class BookingServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def parse_datetime_safe(dt_string: str) -> datetime:
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BookingRepository(Protocol):
    def list_bookings(self) -> List[Dict[str, Any]]:
        pass

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        pass

    def create_booking(self, booking: Dict[str, Any]) -> None:
        pass

    def update_booking(
        self, booking_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    def delete_booking(self, booking_id: str) -> None:
        pass


class DynamoBookingRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-bookings-dev", region_name="us-east-1"
        )

    def list_bookings(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        booking = self.client.get_item(key={"id": booking_id})
        return booking or None

    def create_booking(self, booking: Dict[str, Any]) -> None:
        self.client.put_item(booking)

    def update_booking(
        self, booking_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.client.update_item(key={"id": booking_id}, update_data=update_data)

    def delete_booking(self, booking_id: str) -> None:
        self.client.delete_item(key={"id": booking_id})


@dataclass
class BookingService:
    repository: BookingRepository

    def __init__(self, repository: Optional[BookingRepository] = None):
        self.repository = repository or DynamoBookingRepository()

    def list_bookings(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        bookings = self.repository.list_bookings()

        if user_id:
            bookings = [
                booking for booking in bookings if booking.get("userId") == user_id
            ]

        if status:
            try:
                status_enum = BookingStatus[status.upper()]
            except KeyError as error:
                raise BookingServiceError("Invalid status", 400) from error
            bookings = [
                booking
                for booking in bookings
                if booking.get("status") == status_enum.value
            ]

        return bookings

    def get_booking(self, booking_id: str) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)
        return booking

    def create_booking(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
                raise BookingServiceError(f"{field} is required", 400)

        try:
            start_time = parse_datetime_safe(data["startTime"])
            end_time = parse_datetime_safe(data["endTime"])
        except ValueError as error:
            raise BookingServiceError(
                "Invalid datetime format. Use ISO format.", 400
            ) from error

        if end_time <= start_time:
            raise BookingServiceError("End time must be after start time", 400)

        for existing_booking in self.repository.list_bookings():
            if existing_booking.get("stationId") != data["stationId"]:
                continue
            if existing_booking.get("status") not in [
                BookingStatus.PENDING.value,
                BookingStatus.CONFIRMED.value,
            ]:
                continue

            existing_start = parse_datetime_safe(existing_booking["startTime"])
            existing_end = parse_datetime_safe(existing_booking["endTime"])
            if not (end_time <= existing_start or start_time >= existing_end):
                raise BookingServiceError(
                    "Time slot conflicts with existing booking",
                    409,
                )

        try:
            status = BookingStatus[data.get("status", "PENDING").upper()]
        except KeyError as error:
            raise BookingServiceError("Invalid status", 400) from error

        booking = Booking(
            userId=data["userId"],
            vesselId=data["vesselId"],
            stationId=data["stationId"],
            startTime=start_time,
            endTime=end_time,
            chargerType=data["chargerType"],
            status=status,
        )

        booking_data = booking.to_dict()
        self.repository.create_booking(booking_data)
        return booking_data

    def update_booking(self, booking_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)

        update_data: Dict[str, Any] = {}

        if "status" in data:
            try:
                status_enum = BookingStatus[data["status"].upper()]
            except KeyError as error:
                raise BookingServiceError("Invalid status", 400) from error
            update_data["status"] = status_enum.value

        start_time = parse_datetime_safe(booking["startTime"])
        end_time = parse_datetime_safe(booking["endTime"])

        try:
            if "startTime" in data:
                start_time = parse_datetime_safe(data["startTime"])
                update_data["startTime"] = start_time.isoformat()
            if "endTime" in data:
                end_time = parse_datetime_safe(data["endTime"])
                update_data["endTime"] = end_time.isoformat()
        except ValueError as error:
            raise BookingServiceError(
                "Invalid datetime format. Use ISO format.", 400
            ) from error

        if end_time <= start_time:
            raise BookingServiceError("End time must be after start time", 400)

        return self.repository.update_booking(booking_id, update_data)

    def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)

        if booking.get("status") == BookingStatus.COMPLETED.value:
            raise BookingServiceError("Cannot cancel completed booking", 400)

        return self.repository.update_booking(
            booking_id,
            {"status": BookingStatus.CANCELLED.value},
        )

    def delete_booking(self, booking_id: str) -> None:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)
        self.repository.delete_booking(booking_id)

    def list_upcoming_bookings(self, user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            raise BookingServiceError("userId parameter is required", 400)

        upcoming: List[Dict[str, Any]] = []
        current_time = now_utc()
        for booking in self.repository.list_bookings():
            start_time = parse_datetime_safe(booking["startTime"])
            if (
                booking.get("userId") == user_id
                and start_time > current_time
                and booking.get("status")
                in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]
            ):
                upcoming.append(booking)

        upcoming.sort(key=lambda booking: booking["startTime"])
        return upcoming

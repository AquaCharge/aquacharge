from services.bookings.service import (
    BookingRepository,
    BookingService,
    BookingServiceError,
)
from models.booking import BookingStatus


class InMemoryBookingRepository(BookingRepository):
    def __init__(self, bookings=None):
        self.bookings = bookings or []

    def list_bookings(self):
        return self.bookings

    def get_booking(self, booking_id):
        for booking in self.bookings:
            if booking.get("id") == booking_id:
                return booking
        return None

    def create_booking(self, booking):
        self.bookings.append(booking)

    def update_booking(self, booking_id, update_data):
        booking = self.get_booking(booking_id)
        booking.update(update_data)
        return booking

    def delete_booking(self, booking_id):
        self.bookings = [
            booking for booking in self.bookings if booking.get("id") != booking_id
        ]


def test_create_booking_rejects_time_overlap_conflict():
    repository = InMemoryBookingRepository(
        bookings=[
            {
                "id": "b-1",
                "stationId": "station-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.CONFIRMED.value,
            }
        ]
    )
    service = BookingService(repository=repository)

    try:
        service.create_booking(
            {
                "userId": "u-1",
                "vesselId": "v-1",
                "stationId": "station-1",
                "startTime": "2026-03-04T10:30:00",
                "endTime": "2026-03-04T11:30:00",
                "chargerType": "Type 2 AC",
            }
        )
        assert False, "Expected conflict error"
    except BookingServiceError as error:
        assert error.status_code == 409
        assert error.message == "Time slot conflicts with existing booking"


def test_create_booking_accepts_non_conflicting_slot():
    repository = InMemoryBookingRepository(
        bookings=[
            {
                "id": "b-1",
                "stationId": "station-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.CONFIRMED.value,
            }
        ]
    )
    service = BookingService(repository=repository)

    booking = service.create_booking(
        {
            "userId": "u-1",
            "vesselId": "v-1",
            "stationId": "station-1",
            "startTime": "2026-03-04T11:00:00",
            "endTime": "2026-03-04T12:00:00",
            "chargerType": "Type 2 AC",
        }
    )

    assert booking["stationId"] == "station-1"
    assert booking["status"] == BookingStatus.PENDING.value


def test_update_booking_validates_status_enum():
    repository = InMemoryBookingRepository(
        bookings=[
            {
                "id": "b-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.PENDING.value,
            }
        ]
    )
    service = BookingService(repository=repository)

    try:
        service.update_booking("b-1", {"status": "INVALID"})
        assert False, "Expected status validation error"
    except BookingServiceError as error:
        assert error.status_code == 400
        assert error.message == "Invalid status"


def test_list_upcoming_bookings_requires_user_id():
    service = BookingService(repository=InMemoryBookingRepository())

    try:
        service.list_upcoming_bookings("")
        assert False, "Expected userId error"
    except BookingServiceError as error:
        assert error.status_code == 400
        assert error.message == "userId parameter is required"

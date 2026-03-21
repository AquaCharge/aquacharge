from datetime import datetime

from services.bookings.service import (
    ChargerRepository,
    ContractRepository,
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


class InMemoryChargerRepository(ChargerRepository):
    def __init__(self, chargers=None):
        self.chargers = {charger["id"]: charger for charger in (chargers or [])}

    def get_charger(self, charger_id):
        return self.chargers.get(charger_id)

    def list_station_chargers(self, station_id):
        return [
            charger
            for charger in self.chargers.values()
            if charger.get("chargingStationId") == station_id
        ]


class InMemoryContractRepository(ContractRepository):
    def get_contract(self, contract_id):
        return None

    def list_contracts(self):
        return []

    def update_contract(self, contract_id, update_data):
        raise AssertionError("Contract updates are not expected in these tests")


def _build_service(bookings=None):
    return BookingService(
        repository=InMemoryBookingRepository(bookings),
        charger_repository=InMemoryChargerRepository(
            [
                {
                    "id": "charger-1",
                    "chargingStationId": "station-1",
                    "chargerType": "Type 2 AC",
                    "status": 1,
                }
            ]
        ),
        contract_repository=InMemoryContractRepository(),
        now_provider=lambda: datetime.fromisoformat("2026-03-01T00:00:00+00:00"),
    )


def test_create_booking_rejects_time_overlap_conflict():
    service = _build_service(
        bookings=[
            {
                "id": "b-1",
                "stationId": "station-1",
                "chargerId": "charger-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.CONFIRMED.value,
            }
        ]
    )

    try:
        service.create_booking(
            {
                "userId": "u-1",
                "vesselId": "v-1",
                "stationId": "station-1",
                "chargerId": "charger-1",
                "startTime": "2026-03-04T10:30:00",
                "endTime": "2026-03-04T11:30:00",
            }
        )
        assert False, "Expected conflict error"
    except BookingServiceError as error:
        assert error.status_code == 409
        assert error.message == "Time slot conflicts with existing booking"


def test_create_booking_accepts_non_conflicting_slot():
    service = _build_service(
        bookings=[
            {
                "id": "b-1",
                "stationId": "station-1",
                "chargerId": "charger-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.CONFIRMED.value,
            }
        ]
    )

    booking = service.create_booking(
        {
            "userId": "u-1",
            "vesselId": "v-1",
            "stationId": "station-1",
            "chargerId": "charger-1",
            "startTime": "2026-03-04T11:00:00",
            "endTime": "2026-03-04T12:00:00",
        }
    )

    assert booking["stationId"] == "station-1"
    assert booking["status"] == BookingStatus.CONFIRMED.value


def test_update_booking_validates_status_enum():
    service = _build_service(
        bookings=[
            {
                "id": "b-1",
                "stationId": "station-1",
                "chargerId": "charger-1",
                "startTime": "2026-03-04T10:00:00",
                "endTime": "2026-03-04T11:00:00",
                "status": BookingStatus.PENDING.value,
            }
        ]
    )

    try:
        service.update_booking("b-1", {"status": "INVALID"})
        assert False, "Expected status validation error"
    except BookingServiceError as error:
        assert error.status_code == 400
        assert error.message == "Invalid status"


def test_list_upcoming_bookings_requires_user_id():
    service = _build_service()

    try:
        service.list_upcoming_bookings("")
        assert False, "Expected userId error"
    except BookingServiceError as error:
        assert error.status_code == 400
        assert error.message == "userId parameter is required"

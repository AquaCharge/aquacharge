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
    def __init__(self, contracts=None):
        self.contracts = {contract["id"]: dict(contract) for contract in (contracts or [])}

    def get_contract(self, contract_id):
        return self.contracts.get(contract_id)

    def list_contracts(self):
        return list(self.contracts.values())

    def update_contract(self, contract_id, update_data):
        if contract_id not in self.contracts:
            raise AssertionError("Unknown contract update")
        self.contracts[contract_id].update(update_data)
        return self.contracts[contract_id]


class InMemoryDREventService:
    def __init__(self, events=None):
        self.events = {event["id"]: dict(event) for event in (events or [])}

    def get_event(self, event_id):
        return self.events[event_id]

    def update_event(self, event_id, data):
        self.events[event_id].update(data)
        return self.events[event_id]


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


def test_create_booking_transitions_accepted_event_to_committed():
    contract_repository = InMemoryContractRepository(
        [
            {
                "id": "contract-1",
                "vesselId": "v-1",
                "drEventId": "event-1",
                "vesselName": "Sea Breeze",
                "energyAmount": 100,
                "pricePerKwh": 0.2,
                "totalValue": 20,
                "startTime": "2026-03-04T11:00:00+00:00",
                "endTime": "2026-03-04T12:00:00+00:00",
                "status": "pending",
                "terms": "Standard terms",
                "acceptedAt": "2026-03-03T08:00:00+00:00",
                "createdAt": "2026-03-03T00:00:00+00:00",
                "createdBy": "pso-1",
                "bookingId": None,
            }
        ]
    )
    drevent_service = InMemoryDREventService(
        [{"id": "event-1", "status": "Accepted"}]
    )
    service = BookingService(
        repository=InMemoryBookingRepository(),
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
        contract_repository=contract_repository,
        drevent_service=drevent_service,
        now_provider=lambda: datetime.fromisoformat("2026-03-01T00:00:00+00:00"),
    )

    booking = service.create_booking(
        {
            "userId": "u-1",
            "vesselId": "v-1",
            "stationId": "station-1",
            "chargerId": "charger-1",
            "startTime": "2026-03-04T11:00:00+00:00",
            "endTime": "2026-03-04T12:00:00+00:00",
            "contractId": "contract-1",
        }
    )

    assert booking["chargerId"] == "charger-1"
    assert contract_repository.get_contract("contract-1")["status"] == "active"
    assert contract_repository.get_contract("contract-1")["bookingId"] == booking["id"]
    assert drevent_service.get_event("event-1")["status"] == "Committed"

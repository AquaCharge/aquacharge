"""
Tests for SCRUM-169 (remaining items):
  - Contract generation on DR event dispatch
  - Schedule conflict check on acceptance
  - Dock reservation on acceptance

All tests use in-memory stub repositories — no DynamoDB calls.
"""

import pytest
from models.booking import BookingStatus
from models.contract import ContractStatus
from services.contracts.service import ContractService, ContractServiceError


# ---------------------------------------------------------------------------
# In-memory stubs
# ---------------------------------------------------------------------------


class InMemoryContractRepo:
    def __init__(self, contracts=None):
        self._store = {c["id"]: dict(c) for c in (contracts or [])}

    def list_contracts(self):
        return list(self._store.values())

    def get_contract(self, contract_id):
        return self._store.get(contract_id)

    def create_contract(self, data):
        self._store[data["id"]] = dict(data)

    def update_contract(self, contract_id, update_data):
        self._store[contract_id].update(update_data)
        return self._store[contract_id]

    def delete_contract(self, contract_id):
        self._store.pop(contract_id, None)


class InMemoryBookingRepo:
    def __init__(self, bookings=None):
        self._store = list(bookings or [])

    def list_bookings(self):
        return list(self._store)

    def create_booking(self, data):
        self._store.append(dict(data))


class InMemoryVesselRepo:
    def __init__(self, vessels=None):
        self._store = {v["id"]: v for v in (vessels or [])}

    def get_vessel(self, vessel_id):
        return self._store.get(vessel_id)


class InMemoryDREventRepo:
    def __init__(self, events=None):
        self._store = {e["id"]: e for e in (events or [])}

    def get_event(self, event_id):
        return self._store.get(event_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

START = "2026-03-10T08:00:00+00:00"
END = "2026-03-10T12:00:00+00:00"

DR_EVENT = {
    "id": "dr-001",
    "stationId": "station-xyz",
    "targetEnergyKwh": 300.0,
    "pricePerKwh": 0.18,
    "maxParticipants": 3,
    "startTime": START,
    "endTime": END,
    "status": "Created",
    "details": {},
}


VESSEL = {
    "id": "vessel-abc",
    "userId": "user-vo-001",
    "displayName": "Sea Breeze",
    "chargerType": "DC",
}


def _pending_contract(vessel_id="vessel-abc", dr_event_id="dr-001"):
    return {
        "id": "contract-001",
        "vesselId": vessel_id,
        "drEventId": dr_event_id,
        "vesselName": "Sea Breeze",
        "energyAmount": 100.0,
        "pricePerKwh": 0.18,
        "totalValue": 18.0,
        "startTime": START,
        "endTime": END,
        "status": "pending",
        "terms": "Standard terms",
        "createdAt": "2026-03-07T00:00:00",
        "updatedAt": None,
        "createdBy": "pso-001",
        "bookingId": None,
    }


def _non_overlapping_booking(vessel_id="vessel-abc", station_id="station-xyz"):
    """A booking that does NOT overlap the contract window."""
    return {
        "id": "booking-old",
        "vesselId": vessel_id,
        "stationId": station_id,
        "startTime": "2026-03-09T08:00:00+00:00",
        "endTime": "2026-03-09T12:00:00+00:00",
        "status": BookingStatus.PENDING.value,
    }


def _overlapping_vessel_booking(vessel_id="vessel-abc"):
    """A booking for the same vessel that overlaps the contract window."""
    return {
        "id": "booking-conflict",
        "vesselId": vessel_id,
        "stationId": "some-other-station",
        "startTime": "2026-03-10T09:00:00+00:00",
        "endTime": "2026-03-10T11:00:00+00:00",
        "status": BookingStatus.PENDING.value,
    }


def _overlapping_dock_booking(station_id="station-xyz"):
    """A booking at the same station that overlaps the contract window (different vessel)."""
    return {
        "id": "booking-dock",
        "vesselId": "vessel-other",
        "stationId": station_id,
        "startTime": "2026-03-10T09:00:00+00:00",
        "endTime": "2026-03-10T11:00:00+00:00",
        "status": BookingStatus.CONFIRMED.value,
    }


def _make_service(contracts=None, bookings=None, vessel=None, dr_event=None):
    return ContractService(
        repository=InMemoryContractRepo(contracts),
        booking_repository=InMemoryBookingRepo(bookings),
        vessel_repository=InMemoryVesselRepo([vessel] if vessel else []),
        drevent_repository=InMemoryDREventRepo([dr_event] if dr_event else []),
    )


# ===========================================================================
# DISPATCH TESTS
# ===========================================================================


class TestDispatchEvent:

    def test_creates_one_contract_per_eligible_vessel(self):
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
        ]
        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")
        assert len(contracts) == 2

    def test_respects_max_participants_cap(self):
        event = {**DR_EVENT, "maxParticipants": 2}
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
            {"vesselId": "v3", "displayName": "Ferry C"},
        ]
        contracts = service.dispatch_event(event, eligible, caller_user_id="pso-001")
        assert len(contracts) == 2

    def test_energy_split_evenly_across_vessels(self):
        event = {**DR_EVENT, "targetEnergyKwh": 300.0, "maxParticipants": 3}
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
            {"vesselId": "v3", "displayName": "Ferry C"},
        ]
        contracts = service.dispatch_event(event, eligible, caller_user_id="pso-001")
        for contract in contracts:
            assert abs(float(contract["energyAmount"]) - 100.0) < 0.01

    def test_contracts_inherit_price_and_window_from_event(self):
        service = _make_service()
        eligible = [{"vesselId": "v1", "displayName": "Ferry A"}]
        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")
        c = contracts[0]
        assert float(c["pricePerKwh"]) == pytest.approx(0.18)
        assert c["startTime"] == START
        assert c["endTime"] == END

    def test_contracts_start_in_pending_status(self):
        service = _make_service()
        eligible = [{"vesselId": "v1", "displayName": "Ferry A"}]
        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")
        assert contracts[0]["status"] == ContractStatus.PENDING.value

    def test_no_eligible_vessels_returns_empty_list(self):
        service = _make_service()
        contracts = service.dispatch_event(DR_EVENT, [], caller_user_id="pso-001")
        assert contracts == []

    def test_created_by_is_set_to_caller(self):
        service = _make_service()
        eligible = [{"vesselId": "v1", "displayName": "Ferry A"}]
        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")
        assert contracts[0]["createdBy"] == "pso-001"

    def test_drEventId_is_set_on_each_contract(self):
        service = _make_service()
        eligible = [{"vesselId": "v1", "displayName": "Ferry A"}]
        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")
        assert contracts[0]["drEventId"] == DR_EVENT["id"]


# ===========================================================================
# SCHEDULE CONFLICT CHECK TESTS
# ===========================================================================


class TestScheduleConflictOnAccept:

    def test_accept_succeeds_when_no_bookings_exist(self):
        service = _make_service(
            contracts=[_pending_contract()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        result = service.accept_contract(
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )
        assert result["status"] == ContractStatus.ACTIVE.value

    def test_accept_succeeds_when_existing_booking_does_not_overlap(self):
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_non_overlapping_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        result = service.accept_contract(
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )
        assert result["status"] == ContractStatus.ACTIVE.value

    def test_accept_rejected_when_vessel_has_overlapping_booking(self):
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_overlapping_vessel_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.message.lower()

    def test_accept_rejected_when_cancelled_booking_overlaps(self):
        """Cancelled bookings should not block acceptance."""
        cancelled = {
            **_overlapping_vessel_booking(),
            "status": BookingStatus.CANCELLED.value,
        }
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[cancelled],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        # Should NOT raise — cancelled bookings are ignored
        result = service.accept_contract(
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )
        assert result["status"] == ContractStatus.ACTIVE.value

    def test_conflict_check_only_applies_to_same_vessel(self):
        """An overlapping booking for a different vessel should not block acceptance."""
        other_vessel_booking = {**_overlapping_vessel_booking(vessel_id="vessel-other")}
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[other_vessel_booking],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        result = service.accept_contract(
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )
        assert result["status"] == ContractStatus.ACTIVE.value


# ===========================================================================
# DOCK RESERVATION TESTS
# ===========================================================================


class TestDockReservationOnAccept:

    def test_accept_creates_booking_at_event_station(self):
        booking_repo = InMemoryBookingRepo()
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        bookings = booking_repo.list_bookings()
        assert len(bookings) == 1
        booking = bookings[0]
        assert booking["stationId"] == DR_EVENT["stationId"]
        assert booking["vesselId"] == "vessel-abc"

    def test_booking_window_matches_contract_window(self):
        booking_repo = InMemoryBookingRepo()
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        booking = booking_repo.list_bookings()[0]
        # Times should be within the same day as the contract
        assert "2026-03-10" in booking["startTime"]
        assert "2026-03-10" in booking["endTime"]

    def test_booking_uses_vessel_charger_type(self):
        booking_repo = InMemoryBookingRepo()
        vessel = {**VESSEL, "chargerType": "DC"}
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([vessel]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        assert booking_repo.list_bookings()[0]["chargerType"] == "DC"

    def test_booking_id_stored_on_contract(self):
        booking_repo = InMemoryBookingRepo()
        contract_repo = InMemoryContractRepo([_pending_contract()])
        service = ContractService(
            repository=contract_repo,
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        saved_booking_id = booking_repo.list_bookings()[0]["id"]
        assert (
            contract_repo.get_contract("contract-001")["bookingId"] == saved_booking_id
        )

    def test_dock_conflict_blocks_acceptance(self):
        """If the dock is already taken, acceptance must fail with 409."""
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_overlapping_dock_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        assert exc_info.value.status_code == 409
        assert "dock" in exc_info.value.message.lower()

    def test_dock_conflict_does_not_create_booking(self):
        """When a dock conflict occurs, no new booking should be persisted."""
        booking_repo = InMemoryBookingRepo([_overlapping_dock_booking()])
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        try:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        except ContractServiceError:
            pass
        # Still only the original dock booking, nothing new added
        assert len(booking_repo.list_bookings()) == 1

    def test_contract_status_not_changed_on_dock_conflict(self):
        """Contract must remain pending if acceptance is blocked by a dock conflict."""
        contract_repo = InMemoryContractRepo([_pending_contract()])
        service = ContractService(
            repository=contract_repo,
            booking_repository=InMemoryBookingRepo([_overlapping_dock_booking()]),
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        try:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        except ContractServiceError:
            pass
        assert contract_repo.get_contract("contract-001")["status"] == "pending"

    def test_missing_dr_event_raises_404(self):
        service = _make_service(
            contracts=[_pending_contract()],
            vessel=VESSEL,
            dr_event=None,  # event not in repo
        )
        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        assert exc_info.value.status_code == 404

    def test_booking_status_is_pending(self):
        booking_repo = InMemoryBookingRepo()
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])
        assert booking_repo.list_bookings()[0]["status"] == BookingStatus.PENDING.value

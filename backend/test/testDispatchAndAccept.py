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

    def update_event(self, event_id, update_data):
        self._store[event_id].update(update_data)
        return self._store[event_id]


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
        "energyAmount": 0.0,
        "pricePerKwh": 0.18,
        "totalValue": 0.0,
        "startTime": START,
        "endTime": END,
        "status": "pending",
        "terms": "Standard terms",
        "committedPowerKw": None,
        "operatorNotes": "",
        "acceptedAt": None,
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

    def test_dispatch_creates_contracts_for_all_eligible_vessels(self):
        event = {**DR_EVENT, "maxParticipants": 2}
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
            {"vesselId": "v3", "displayName": "Ferry C"},
        ]
        contracts = service.dispatch_event(event, eligible, caller_user_id="pso-001")
        assert len(contracts) == 3

    def test_pending_offers_do_not_preallocate_event_energy(self):
        event = {**DR_EVENT, "targetEnergyKwh": 300.0, "maxParticipants": 3}
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
            {"vesselId": "v3", "displayName": "Ferry C"},
        ]
        contracts = service.dispatch_event(event, eligible, caller_user_id="pso-001")
        for contract in contracts:
            assert float(contract["energyAmount"]) == pytest.approx(0.0)
            assert float(contract["totalValue"]) == pytest.approx(0.0)

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

    def test_dispatch_skips_existing_contract_for_same_event_and_vessel(self):
        existing_contract = {
            **_pending_contract(vessel_id="v1"),
            "id": "contract-existing",
            "drEventId": DR_EVENT["id"],
            "vesselName": "Ferry A",
        }
        service = _make_service(contracts=[existing_contract])
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v2", "displayName": "Ferry B"},
        ]

        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")

        assert len(contracts) == 1
        assert contracts[0]["vesselId"] == "v2"

    def test_dispatch_ignores_duplicate_eligible_rows_for_same_vessel(self):
        service = _make_service()
        eligible = [
            {"vesselId": "v1", "displayName": "Ferry A"},
            {"vesselId": "v1", "displayName": "Ferry A"},
        ]

        contracts = service.dispatch_event(DR_EVENT, eligible, caller_user_id="pso-001")

        assert len(contracts) == 1
        assert contracts[0]["vesselId"] == "v1"

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
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45, "operatorNotes": "Ready to discharge"},
        )
        assert result["status"] == ContractStatus.PENDING.value
        assert result["committedPowerKw"] == 45
        assert result["energyAmount"] == pytest.approx(45.0)
        assert float(result["totalValue"]) == pytest.approx(8.1)

    def test_accept_succeeds_when_existing_booking_does_not_overlap(self):
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_non_overlapping_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        result = service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert result["status"] == ContractStatus.PENDING.value

    def test_accept_rejected_when_vessel_has_overlapping_booking(self):
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_overlapping_vessel_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 45},
            )
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.message.lower()

    def test_accept_handles_existing_booking_with_naive_datetimes(self):
        naive_booking = {
            "id": "booking-naive",
            "vesselId": "vessel-other",
            "stationId": "station-other",
            "startTime": "2026-03-10T13:00:00",
            "endTime": "2026-03-10T14:00:00",
            "status": BookingStatus.PENDING.value,
        }
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[naive_booking],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )

        result = service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )

        assert result["status"] == ContractStatus.PENDING.value

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
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert result["status"] == ContractStatus.PENDING.value

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
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert result["status"] == ContractStatus.PENDING.value


# ===========================================================================
# BOOKING HANDOFF TESTS
# ===========================================================================


class TestBookingHandoffOnAccept:

    def test_accept_does_not_create_booking_at_event_station(self):
        booking_repo = InMemoryBookingRepo()
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        bookings = booking_repo.list_bookings()
        assert bookings == []

    def test_accept_keeps_booking_id_empty_until_booking_confirmation(self):
        contract_repo = InMemoryContractRepo([_pending_contract()])
        service = ContractService(
            repository=contract_repo,
            booking_repository=InMemoryBookingRepo(),
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert contract_repo.get_contract("contract-001")["bookingId"] is None

    def test_station_dock_conflicts_do_not_block_acceptance(self):
        service = _make_service(
            contracts=[_pending_contract()],
            bookings=[_overlapping_dock_booking()],
            vessel=VESSEL,
            dr_event=DR_EVENT,
        )
        result = service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert result["status"] == ContractStatus.PENDING.value

    def test_station_dock_conflict_does_not_create_booking(self):
        booking_repo = InMemoryBookingRepo([_overlapping_dock_booking()])
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=booking_repo,
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert len(booking_repo.list_bookings()) == 1

    def test_contract_status_remains_pending_after_accept(self):
        contract_repo = InMemoryContractRepo([_pending_contract()])
        service = ContractService(
            repository=contract_repo,
            booking_repository=InMemoryBookingRepo([_overlapping_dock_booking()]),
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=InMemoryDREventRepo([DR_EVENT]),
        )
        service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )
        assert contract_repo.get_contract("contract-001")["status"] == "pending"

    def test_missing_dr_event_raises_404(self):
        service = _make_service(
            contracts=[_pending_contract()],
            vessel=VESSEL,
            dr_event=None,  # event not in repo
        )
        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 45},
            )
        assert exc_info.value.status_code == 404

    def test_accept_rejects_commitment_above_max_discharge_rate(self):
        low_rate_vessel = {**VESSEL, "maxDischargeRate": 30}
        service = _make_service(
            contracts=[_pending_contract()],
            vessel=low_rate_vessel,
            dr_event=DR_EVENT,
        )

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 45},
            )

        assert exc_info.value.status_code == 400
        assert "maximum discharge rate" in exc_info.value.message

    def test_accept_transitions_dispatched_event_to_accepted(self):
        dispatched_event = {**DR_EVENT, "status": "Dispatched"}
        drevent_repo = InMemoryDREventRepo([dispatched_event])
        service = ContractService(
            repository=InMemoryContractRepo([_pending_contract()]),
            booking_repository=InMemoryBookingRepo([]),
            vessel_repository=InMemoryVesselRepo([VESSEL]),
            drevent_repository=drevent_repo,
        )

        service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 45},
        )

        assert drevent_repo.get_event("dr-001")["status"] == "Accepted"

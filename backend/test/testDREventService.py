from datetime import datetime, timedelta, timezone

import pytest

from models.drevent import DREvent, parse_event_status
from services.drevents.service import DREventService, DREventServiceError


class InMemoryEventRepository:
    def __init__(self, events=None):
        self.events = {event["id"]: dict(event) for event in (events or [])}

    def list_events(self):
        return list(self.events.values())

    def get_event(self, event_id):
        event = self.events.get(event_id)
        return dict(event) if event else None

    def put_event(self, event_data):
        self.events[event_data["id"]] = dict(event_data)

    def update_event(self, event_id, update_data):
        self.events[event_id].update(update_data)
        return dict(self.events[event_id])


class InMemoryMeasurementRepository:
    def __init__(self, measurements=None):
        self.measurements = list(measurements or [])

    def list_measurements(self):
        return list(self.measurements)


class InMemoryStationRepository:
    def __init__(self, stations=None):
        self.stations = {station["id"]: dict(station) for station in (stations or [])}

    def get_station(self, station_id):
        station = self.stations.get(station_id)
        return dict(station) if station else None


def make_event(status="Created", event_id="event-1", station_id="station-1"):
    now = datetime.now(timezone.utc)
    return {
        "id": event_id,
        "stationId": station_id,
        "pricePerKwh": 0.25,
        "targetEnergyKwh": 200.0,
        "maxParticipants": 4,
        "startTime": (now + timedelta(hours=1)).isoformat(),
        "endTime": (now + timedelta(hours=4)).isoformat(),
        "status": status,
        "details": {},
        "createdAt": now.isoformat(),
    }


def create_service(events=None, measurements=None, stations=None):
    return DREventService(
        event_repository=InMemoryEventRepository(events),
        measurement_repository=InMemoryMeasurementRepository(measurements),
        station_repository=InMemoryStationRepository(stations or [{"id": "station-1", "city": "Moncton", "provinceOrState": "NB", "country": "Canada"}]),
    )


def test_create_event_defaults_to_created():
    service = create_service(events=[])

    created = service.create_event(
        {
            "stationId": "station-1",
            "pricePerKwh": 0.4,
            "targetEnergyKwh": 120,
            "maxParticipants": 3,
            "startTime": "2026-03-07T10:00:00+00:00",
            "endTime": "2026-03-07T12:00:00+00:00",
            "details": {"minimumSoc": 20},
        }
    )

    assert created["status"] == "Created"
    assert created["stationId"] == "station-1"


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("Created", "Dispatched"),
        ("Dispatched", "Accepted"),
        ("Accepted", "Committed"),
        ("Committed", "Active"),
        ("Active", "Completed"),
        ("Completed", "Settled"),
        ("Settled", "Archived"),
        ("Created", "Cancelled"),
    ],
)
def test_valid_status_transitions_are_allowed(current_status, next_status):
    service = create_service(events=[make_event(status=current_status)])

    updated = service.update_event("event-1", {"status": next_status})

    assert updated["status"] == next_status


def test_invalid_status_transition_is_rejected():
    service = create_service(events=[make_event(status="Created")])

    with pytest.raises(DREventServiceError) as error:
        service.update_event("event-1", {"status": "Completed"})

    assert error.value.status_code == 400
    assert "Invalid status transition" in error.value.message


def test_monitoring_snapshot_aggregates_measurements():
    now = datetime.now(timezone.utc)
    measurements = [
        {
            "id": "m1",
            "drEventId": "event-1",
            "contractId": "contract-1",
            "vesselId": "vessel-1",
            "timestamp": (now - timedelta(minutes=20)).isoformat(),
            "energyKwh": 30,
            "powerKw": 12,
            "currentSOC": 58,
        },
        {
            "id": "m2",
            "drEventId": "event-1",
            "contractId": "contract-2",
            "vesselId": "vessel-2",
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "energyKwh": 45,
            "powerKw": 16,
            "currentSOC": 61,
        },
        {
            "id": "m3",
            "drEventId": "event-1",
            "contractId": "contract-1",
            "vesselId": "vessel-1",
            "timestamp": (now - timedelta(minutes=5)).isoformat(),
            "energyKwh": 15,
            "powerKw": 18,
            "currentSOC": 54,
        },
    ]
    service = create_service(events=[make_event(status="Active")], measurements=measurements)

    snapshot = service.get_monitoring_snapshot(event_id="event-1", region="Moncton", period_hours=24)

    assert snapshot["summary"]["totalEnergyDeliveredKwh"] == 90.0
    assert snapshot["summary"]["activeVessels"] == 2
    assert snapshot["summary"]["eventStatus"] == "Active"
    assert snapshot["baselineAvailable"] is False
    assert len(snapshot["vesselRates"]) == 2
    assert len(snapshot["vesselCurve"]) == 2
    assert snapshot["vesselCurve"][0]["vesselId"] == "vessel-1"
    assert len(snapshot["vesselCurve"][0]["points"]) == 2
    assert snapshot["vesselCurve"][0]["totalEnergyDischargedKwh"] == 45.0
    assert snapshot["vesselCurve"][0]["points"][0]["energyDischargedKwh"] == 30.0
    assert snapshot["vesselCurve"][0]["points"][1]["cumulativeEnergyDischargedKwh"] == 45.0
    assert snapshot["vesselRates"][0]["dischargeRateKw"] == 18.0
    assert len(snapshot["loadCurve"]) == 3
    assert snapshot["loadCurve"][0]["energyDischargedKwh"] == 30.0
    assert snapshot["loadCurve"][-1]["cumulativeEnergyDischargedKwh"] == 90.0


def test_monitoring_snapshot_returns_empty_state_for_no_measurements():
    service = create_service(events=[make_event(status="Dispatched")], measurements=[])

    snapshot = service.get_monitoring_snapshot(event_id="event-1", period_hours=24)

    assert snapshot["empty"] is True
    assert snapshot["summary"]["totalEnergyDeliveredKwh"] == 0.0
    assert snapshot["vesselRates"] == []
    assert snapshot["vesselCurve"] == []


def test_from_dict_accepts_legacy_uppercase_status():
    event = DREvent.from_dict(make_event(status="ACTIVE"))

    assert event.status.value == "Active"
    assert event.to_public_dict()["status"] == "Active"


def test_parse_event_status_rejects_unknown_status():
    with pytest.raises(ValueError) as error:
        parse_event_status("NOT_A_REAL_STATUS")

    assert "'NOT_A_REAL_STATUS' is not a valid EventStatus" == str(error.value)


def test_list_events_accepts_legacy_uppercase_status():
    service = create_service(events=[make_event(status="ACTIVE")])

    events = service.list_events()

    assert len(events) == 1
    assert events[0]["status"] == "Active"


def test_monitoring_snapshot_accepts_legacy_uppercase_event_status():
    now = datetime.now(timezone.utc)
    measurements = [
        {
            "id": "m1",
            "drEventId": "event-1",
            "contractId": "contract-1",
            "vesselId": "vessel-1",
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "energyKwh": 12,
            "powerKw": 9,
            "currentSOC": 72,
        }
    ]
    service = create_service(events=[make_event(status="ACTIVE")], measurements=measurements)

    snapshot = service.get_monitoring_snapshot(event_id="event-1", period_hours=24)

    assert snapshot["selectedEvent"]["status"] == "Active"
    assert snapshot["summary"]["eventStatus"] == "Active"


def test_create_event_ignores_contract_id_in_payload():
    service = create_service(events=[])

    created = service.create_event(
        {
            "stationId": "station-1",
            "pricePerKwh": 0.4,
            "targetEnergyKwh": 120,
            "maxParticipants": 3,
            "startTime": "2026-03-07T10:00:00+00:00",
            "endTime": "2026-03-07T12:00:00+00:00",
            "details": {},
            "contractId": "should-not-persist",
        }
    )

    assert "contractId" not in created
    stored = service.event_repository.get_event(created["id"])
    assert "contractId" not in stored


def test_update_event_ignores_contract_id_in_payload():
    service = create_service(events=[make_event(status="Created")])

    updated = service.update_event(
        "event-1",
        {
            "status": "Dispatched",
            "contractId": "should-not-persist",
        },
    )

    assert "contractId" not in updated
    stored = service.event_repository.get_event("event-1")
    assert "contractId" not in stored

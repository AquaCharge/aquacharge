import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import demo_data_setup as demo_script
from db.dynamoClient import DynamoClient
from models.measurments import Measurement
from services.drevents import DREventService
import config


def _client(table_name: str) -> DynamoClient:
    return DynamoClient(table_name=table_name, region_name=config.AWS_REGION)


def _seed_demo_users():
    dev_accounts = demo_script._demo_accounts_for_environment("dev")
    users_client = _client(config.USERS_TABLE)
    users_client.put_item(
        {
            "id": "user-sarah-demo",
            "displayName": "Sarah Chen",
            "email": dev_accounts["vo_email"],
            "passwordHash": "hash",
            "role": 2,
            "type": 1,
            "active": True,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    users_client.put_item(
        {
            "id": "user-robert-demo",
            "displayName": "Robert Wilson",
            "email": dev_accounts["pso_email"],
            "passwordHash": "hash",
            "role": 2,
            "type": 2,
            "active": True,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )


def _seed_stale_demo_data():
    vessel_id = "stale-sarah-vessel"
    event_id = "stale-demo-event"
    booking_id = "stale-demo-booking"
    contract_id = "stale-demo-contract"
    unrelated_event_id = "stale-created-other-station"
    unrelated_contract_id = "stale-pending-other-station"
    unrelated_booking_id = "stale-booking-other-station"
    stale_station_id = "stale-test-station"
    stale_charger_id = "stale-test-charger"

    _client(config.STATIONS_TABLE).put_item(
        {
            "id": stale_station_id,
            "displayName": "Test Dock",
            "longitude": Decimal("-66.06"),
            "latitude": Decimal("45.27"),
            "city": "Saint John",
            "provinceOrState": "NB",
            "country": "Canada",
            "status": 1,
        }
    )
    _client(config.CHARGERS_TABLE).put_item(
        {
            "id": stale_charger_id,
            "chargingStationId": stale_station_id,
            "chargerType": "CCS",
            "maxRate": Decimal("50"),
            "status": 1,
        }
    )

    _client(config.VESSELS_TABLE).put_item(
        {
            "id": vessel_id,
            "userId": "user-sarah-demo",
            "displayName": "Old Demo Vessel",
            "vesselType": "electric_ferry",
            "chargerType": "CCS",
            "capacity": Decimal("45"),
            "maxCapacity": Decimal("90"),
            "maxChargeRate": Decimal("30"),
            "minChargeRate": Decimal("10"),
            "maxDischargeRate": Decimal("25"),
            "longitude": Decimal("-63.57"),
            "latitude": Decimal("44.64"),
            "rangeMeters": Decimal("10000"),
            "active": True,
            "createdAt": "2026-01-10T00:00:00+00:00",
        }
    )
    _client(config.BOOKINGS_TABLE).put_item(
        {
            "id": booking_id,
            "userId": "user-sarah-demo",
            "vesselId": vessel_id,
            "stationId": demo_script.DEMO_STATION_IDS["halifax"],
            "chargerId": demo_script.DEMO_CHARGER_IDS["halifax-1"],
            "chargerType": "CCS",
            "startTime": "2026-02-01T10:00:00+00:00",
            "endTime": "2026-02-01T12:00:00+00:00",
            "status": 2,
            "createdAt": "2026-02-01T08:00:00+00:00",
        }
    )
    _client(config.BOOKINGS_TABLE).put_item(
        {
            "id": unrelated_booking_id,
            "userId": "someone-else",
            "vesselId": "someone-else-vessel",
            "stationId": stale_station_id,
            "chargerId": stale_charger_id,
            "chargerType": "CCS",
            "startTime": "2026-03-01T10:00:00+00:00",
            "endTime": "2026-03-01T12:00:00+00:00",
            "status": 1,
            "createdAt": "2026-03-01T08:00:00+00:00",
        }
    )
    _client(config.DREVENTS_TABLE).put_item(
        {
            "id": event_id,
            "stationId": demo_script.DEMO_STATION_IDS["halifax"],
            "pricePerKwh": Decimal("0.30"),
            "targetEnergyKwh": Decimal("80"),
            "maxParticipants": 1,
            "startTime": "2026-02-01T10:00:00+00:00",
            "endTime": "2026-02-01T12:00:00+00:00",
            "status": "Completed",
            "details": {"scenario": "stale"},
            "createdAt": "2026-02-01T07:00:00+00:00",
        }
    )
    _client(config.DREVENTS_TABLE).put_item(
        {
            "id": unrelated_event_id,
            "stationId": stale_station_id,
            "pricePerKwh": Decimal("10"),
            "targetEnergyKwh": Decimal("100"),
            "maxParticipants": 10,
            "startTime": "2026-03-09T17:00:00+00:00",
            "endTime": "2026-03-10T17:00:00+00:00",
            "status": "Created",
            "details": {"scenario": "stale-unrelated"},
            "createdAt": "2026-03-09T16:30:00+00:00",
        }
    )
    _client(config.CONTRACTS_TABLE).put_item(
        {
            "id": contract_id,
            "bookingId": booking_id,
            "vesselId": vessel_id,
            "drEventId": event_id,
            "vesselName": "Old Demo Vessel",
            "energyAmount": Decimal("60"),
            "pricePerKwh": Decimal("0.30"),
            "totalValue": Decimal("18"),
            "startTime": "2026-02-01T10:00:00+00:00",
            "endTime": "2026-02-01T12:00:00+00:00",
            "status": "completed",
            "terms": "stale",
            "committedPowerKw": Decimal("30"),
            "operatorNotes": "stale",
            "acceptedAt": "2026-02-01T09:00:00+00:00",
            "createdAt": "2026-02-01T07:00:00+00:00",
            "updatedAt": "2026-02-01T12:05:00+00:00",
            "createdBy": "user-robert-demo",
        }
    )
    _client(config.CONTRACTS_TABLE).put_item(
        {
            "id": unrelated_contract_id,
            "bookingId": unrelated_booking_id,
            "vesselId": "someone-else-vessel",
            "drEventId": unrelated_event_id,
            "vesselName": "Other Vessel",
            "energyAmount": Decimal("100"),
            "pricePerKwh": Decimal("10"),
            "totalValue": Decimal("1000"),
            "startTime": "2026-03-09T17:00:00+00:00",
            "endTime": "2026-03-10T17:00:00+00:00",
            "status": "pending",
            "terms": "stale pending contract",
            "createdAt": "2026-03-09T16:30:00+00:00",
            "createdBy": "someone-else",
        }
    )
    measurement = Measurement(
        id="stale-measurement-1",
        vesselId=vessel_id,
        contractId=contract_id,
        drEventId=event_id,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        energyKwh=10,
        powerKw=20,
        currentSOC=60,
    )
    _client(config.MEASUREMENTS_TABLE).put_item(measurement.to_dict())
    unrelated_measurement = Measurement(
        id="stale-measurement-other-station",
        vesselId="someone-else-vessel",
        contractId=unrelated_contract_id,
        drEventId=unrelated_event_id,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
        energyKwh=5,
        powerKw=10,
        currentSOC=50,
    )
    _client(config.MEASUREMENTS_TABLE).put_item(unrelated_measurement.to_dict())


def test_demo_data_dry_run_is_non_mutating(monkeypatch):
    _seed_demo_users()
    _seed_stale_demo_data()

    monkeypatch.setattr(sys, "argv", ["setup_demo_data.py"])
    exit_code = demo_script.main()

    assert exit_code == 0
    assert _client(config.VESSELS_TABLE).get_item({"id": "stale-sarah-vessel"})["id"] == "stale-sarah-vessel"
    assert _client(config.CONTRACTS_TABLE).get_item({"id": "stale-demo-contract"})["id"] == "stale-demo-contract"


def test_demo_data_apply_reseeds_history_and_updates_dashboards(monkeypatch):
    _seed_demo_users()
    _seed_stale_demo_data()

    monkeypatch.setattr(sys, "argv", ["setup_demo_data.py", "--apply"])
    exit_code = demo_script.main()

    assert exit_code == 0
    assert _client(config.STATIONS_TABLE).get_item({"id": "stale-test-station"}) == {}
    assert _client(config.CHARGERS_TABLE).get_item({"id": "stale-test-charger"}) == {}
    assert _client(config.VESSELS_TABLE).get_item({"id": "stale-sarah-vessel"}) == {}
    assert _client(config.CONTRACTS_TABLE).get_item({"id": "stale-demo-contract"}) == {}
    assert _client(config.CONTRACTS_TABLE).get_item({"id": "stale-pending-other-station"}) == {}
    assert _client(config.DREVENTS_TABLE).get_item({"id": "stale-created-other-station"}) == {}
    assert _client(config.BOOKINGS_TABLE).get_item({"id": "stale-booking-other-station"}) == {}
    assert _client(config.MEASUREMENTS_TABLE).get_item({"id": "stale-measurement-other-station"}) == {}

    sarah_user = _client(config.USERS_TABLE).get_item({"id": "user-sarah-demo"})
    assert sarah_user["currentVesselId"] == demo_script.DEMO_VESSEL_ID

    seeded_vessel = _client(config.VESSELS_TABLE).get_item({"id": demo_script.DEMO_VESSEL_ID})
    assert seeded_vessel["displayName"] == "Harbor Spirit"
    seeded_stations = _client(config.STATIONS_TABLE).scan_items()
    seeded_station_ids = {item["id"] for item in seeded_stations}
    assert seeded_station_ids == set(demo_script.DEMO_STATION_IDS.values())
    seeded_events = _client(config.DREVENTS_TABLE).scan_items()
    assert len(seeded_events) == len(demo_script.DEMO_EVENT_IDS)
    assert all(item["status"] in {"Completed", "Archived"} for item in seeded_events)

    monitoring = DREventService().get_monitoring_snapshot(
        event_id=demo_script.DEMO_EVENT_IDS["completed"],
        period_hours=24,
    )
    analytics = DREventService().get_analytics_snapshot(period_hours=168)

    assert monitoring["empty"] is False
    assert monitoring["summary"]["totalEnergyDeliveredKwh"] > 0
    assert analytics["empty"] is False
    assert analytics["summary"]["eventsConsidered"] == len(demo_script.DEMO_EVENT_IDS)
    assert len(analytics["timeSeries"]) >= 5
    assert len(analytics["financials"]["timeSeries"]) >= 5


def test_demo_data_rejects_prod_apply_without_confirmation(monkeypatch):
    monkeypatch.setattr(demo_script.config, "ENVIRONMENT", "prod")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup_demo_data.py",
            "--target-environment",
            "prod",
            "--apply",
        ],
    )

    exit_code = demo_script.main()

    assert exit_code == 2


def test_demo_data_rejects_when_target_environment_mismatches_runtime(monkeypatch):
    monkeypatch.setattr(demo_script.config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup_demo_data.py",
            "--target-environment",
            "prod",
        ],
    )

    exit_code = demo_script.main()

    assert exit_code == 2


def test_demo_data_uses_prod_account_mapping():
    prod_accounts = demo_script._demo_accounts_for_environment("prod")

    assert prod_accounts["vo_email"] == "sarah.chen@aquacharge.demo"
    assert prod_accounts["pso_email"] == "alex.rivera@aquacharge.demo"

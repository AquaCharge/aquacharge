#!/usr/bin/env python3
"""Prepare a repeatable AquaCharge demo dataset in shared *-dev tables."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

from boto3.dynamodb.conditions import Key

import config
from db.dynamoClient import DynamoClient
from models.booking import Booking, BookingStatus
from models.charger import Charger, ChargerStatus
from models.contract import Contract, ContractStatus
from models.drevent import DREvent, EventStatus
from models.measurments import Measurement
from models.station import Station, StationStatus
from models.vessel import Vessel

SARAH_EMAIL = "sarah.chen@bayshipping.com"
ROBERT_EMAIL = "robert.wilson@gridoperator.com"

DEMO_STATION_IDS = {
    "moncton": "demo-station-moncton",
    "saint-john": "demo-station-saint-john",
    "halifax": "demo-station-halifax",
}
DEMO_CHARGER_IDS = {
    "moncton-1": "demo-charger-moncton-1",
    "moncton-2": "demo-charger-moncton-2",
    "saint-john-1": "demo-charger-saint-john-1",
    "saint-john-2": "demo-charger-saint-john-2",
    "halifax-1": "demo-charger-halifax-1",
    "halifax-2": "demo-charger-halifax-2",
}
DEMO_VESSEL_ID = "demo-vessel-sarah-halifax"
DEMO_EVENT_IDS = {
    "completed": "demo-drevent-halifax-completed",
    "completed-2": "demo-drevent-saint-john-completed-2",
    "completed-3": "demo-drevent-moncton-completed-3",
    "completed-4": "demo-drevent-halifax-completed-4",
    "completed-5": "demo-drevent-saint-john-completed-5",
    "archived": "demo-drevent-moncton-archived",
}
DEMO_CONTRACT_IDS = {
    "completed": "demo-contract-halifax-completed",
    "completed-2": "demo-contract-saint-john-completed-2",
    "completed-3": "demo-contract-moncton-completed-3",
    "completed-4": "demo-contract-halifax-completed-4",
    "completed-5": "demo-contract-saint-john-completed-5",
    "archived": "demo-contract-moncton-archived",
}
DEMO_BOOKING_IDS = {
    "completed": "demo-booking-halifax-completed",
    "completed-2": "demo-booking-saint-john-completed-2",
    "completed-3": "demo-booking-moncton-completed-3",
    "completed-4": "demo-booking-halifax-completed-4",
    "completed-5": "demo-booking-saint-john-completed-5",
    "archived": "demo-booking-moncton-archived",
}


def _as_decimal(value: float | str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _to_dynamo(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(value, float):
            normalized[key] = Decimal(str(value))
        elif isinstance(value, dict):
            normalized[key] = _to_dynamo(value)
        elif isinstance(value, list):
            normalized[key] = [
                _to_dynamo(entry) if isinstance(entry, dict) else entry for entry in value
            ]
        else:
            normalized[key] = value
    return normalized


def _client(table_name: str) -> DynamoClient:
    return DynamoClient(table_name=table_name, region_name=config.AWS_REGION)


def _safe_query_items(
    client: DynamoClient,
    index_name: str,
    key_expression,
    fallback_match,
) -> List[Dict[str, Any]]:
    try:
        return client.query_gsi(index_name=index_name, key_condition_expression=key_expression)
    except Exception:
        return [item for item in client.scan_items() if fallback_match(item)]


def _find_user_by_email(users_client: DynamoClient, email: str) -> Dict[str, Any] | None:
    matches = _safe_query_items(
        users_client,
        "email-index",
        Key("email").eq(email),
        lambda item: str(item.get("email") or "").lower() == email.lower(),
    )
    return matches[0] if matches else None


def _list_user_vessels(vessels_client: DynamoClient, user_id: str) -> List[Dict[str, Any]]:
    return _safe_query_items(
        vessels_client,
        "userId-index",
        Key("userId").eq(user_id),
        lambda item: str(item.get("userId") or "") == user_id,
    )


@dataclass
class MutationPlan:
    deletes: Dict[str, List[str]]
    puts: Dict[str, List[Dict[str, Any]]]
    user_updates: List[Dict[str, Any]]


def _build_demo_stations() -> List[Dict[str, Any]]:
    return [
        Station(
            id=DEMO_STATION_IDS["moncton"],
            displayName="AquaCharge Demo Station - Moncton",
            longitude=_as_decimal("-64.7782"),
            latitude=_as_decimal("46.0878"),
            city="Moncton",
            provinceOrState="NB",
            country="Canada",
            status=StationStatus.ACTIVE,
        ).to_dict(),
        Station(
            id=DEMO_STATION_IDS["saint-john"],
            displayName="AquaCharge Demo Station - Saint John",
            longitude=_as_decimal("-66.0570"),
            latitude=_as_decimal("45.2733"),
            city="Saint John",
            provinceOrState="NB",
            country="Canada",
            status=StationStatus.ACTIVE,
        ).to_dict(),
        Station(
            id=DEMO_STATION_IDS["halifax"],
            displayName="AquaCharge Demo Station - Halifax",
            longitude=_as_decimal("-63.5752"),
            latitude=_as_decimal("44.6488"),
            city="Halifax",
            provinceOrState="NS",
            country="Canada",
            status=StationStatus.ACTIVE,
        ).to_dict(),
    ]


def _build_demo_chargers() -> List[Dict[str, Any]]:
    return [
        Charger(
            id=DEMO_CHARGER_IDS["moncton-1"],
            chargingStationId=DEMO_STATION_IDS["moncton"],
            chargerType="CCS",
            maxRate=_as_decimal("50"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
        Charger(
            id=DEMO_CHARGER_IDS["moncton-2"],
            chargingStationId=DEMO_STATION_IDS["moncton"],
            chargerType="CCS",
            maxRate=_as_decimal("75"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
        Charger(
            id=DEMO_CHARGER_IDS["saint-john-1"],
            chargingStationId=DEMO_STATION_IDS["saint-john"],
            chargerType="CCS",
            maxRate=_as_decimal("60"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
        Charger(
            id=DEMO_CHARGER_IDS["saint-john-2"],
            chargingStationId=DEMO_STATION_IDS["saint-john"],
            chargerType="CCS",
            maxRate=_as_decimal("90"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
        Charger(
            id=DEMO_CHARGER_IDS["halifax-1"],
            chargingStationId=DEMO_STATION_IDS["halifax"],
            chargerType="CCS",
            maxRate=_as_decimal("120"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
        Charger(
            id=DEMO_CHARGER_IDS["halifax-2"],
            chargingStationId=DEMO_STATION_IDS["halifax"],
            chargerType="CCS",
            maxRate=_as_decimal("120"),
            status=ChargerStatus.ACTIVE,
        ).to_dict(),
    ]


def _build_demo_vessel(sarah_user_id: str) -> Dict[str, Any]:
    vessel = Vessel(
        id=DEMO_VESSEL_ID,
        userId=sarah_user_id,
        displayName="Harbor Spirit",
        vesselType="electric_ferry",
        chargerType="CCS",
        capacity=96.0,
        maxCapacity=120.0,
        maxChargeRate=75.0,
        minChargeRate=15.0,
        maxDischargeRate=48.0,
        longitude=-63.5745,
        latitude=44.6496,
        rangeMeters=12000.0,
        active=True,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return vessel.to_dict()


def _build_historical_records(
    sarah_user_id: str,
    robert_user_id: str,
    now: datetime,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    event_specs = [
        {
            "key": "completed",
            "stationId": DEMO_STATION_IDS["halifax"],
            "chargerId": DEMO_CHARGER_IDS["halifax-1"],
            "status": EventStatus.COMPLETED,
            "pricePerKwh": Decimal("0.32"),
            "targetEnergyKwh": Decimal("120"),
            "energyAmount": Decimal("96"),
            "powerKw": [24, 28, 22, 18],
            "energyKwh": [24, 28, 22, 22],
            "startTime": now - timedelta(hours=10),
            "endTime": now - timedelta(hours=7),
        },
        {
            "key": "completed-2",
            "stationId": DEMO_STATION_IDS["saint-john"],
            "chargerId": DEMO_CHARGER_IDS["saint-john-1"],
            "status": EventStatus.COMPLETED,
            "pricePerKwh": Decimal("0.29"),
            "targetEnergyKwh": Decimal("150"),
            "energyAmount": Decimal("120"),
            "powerKw": [30, 26, 22, 18],
            "energyKwh": [30, 30, 30, 30],
            "startTime": now - timedelta(days=1, hours=5),
            "endTime": now - timedelta(days=1, hours=2),
        },
        {
            "key": "completed-3",
            "stationId": DEMO_STATION_IDS["moncton"],
            "chargerId": DEMO_CHARGER_IDS["moncton-1"],
            "status": EventStatus.COMPLETED,
            "pricePerKwh": Decimal("0.27"),
            "targetEnergyKwh": Decimal("90"),
            "energyAmount": Decimal("72"),
            "powerKw": [18, 18, 18, 18],
            "energyKwh": [18, 18, 18, 18],
            "startTime": now - timedelta(days=2, hours=6),
            "endTime": now - timedelta(days=2, hours=2),
        },
        {
            "key": "completed-4",
            "stationId": DEMO_STATION_IDS["halifax"],
            "chargerId": DEMO_CHARGER_IDS["halifax-2"],
            "status": EventStatus.COMPLETED,
            "pricePerKwh": Decimal("0.31"),
            "targetEnergyKwh": Decimal("110"),
            "energyAmount": Decimal("88"),
            "powerKw": [26, 22, 20, 20],
            "energyKwh": [22, 22, 22, 22],
            "startTime": now - timedelta(days=3, hours=4),
            "endTime": now - timedelta(days=3, hours=1),
        },
        {
            "key": "completed-5",
            "stationId": DEMO_STATION_IDS["saint-john"],
            "chargerId": DEMO_CHARGER_IDS["saint-john-2"],
            "status": EventStatus.COMPLETED,
            "pricePerKwh": Decimal("0.30"),
            "targetEnergyKwh": Decimal("140"),
            "energyAmount": Decimal("112"),
            "powerKw": [28, 28, 28, 28],
            "energyKwh": [28, 28, 28, 28],
            "startTime": now - timedelta(days=5, hours=3),
            "endTime": now - timedelta(days=5),
        },
        {
            "key": "archived",
            "stationId": DEMO_STATION_IDS["moncton"],
            "chargerId": DEMO_CHARGER_IDS["moncton-1"],
            "status": EventStatus.ARCHIVED,
            "pricePerKwh": Decimal("0.27"),
            "targetEnergyKwh": Decimal("90"),
            "energyAmount": Decimal("72"),
            "powerKw": [18, 18, 18, 18],
            "energyKwh": [18, 18, 18, 18],
            "startTime": now - timedelta(days=6, hours=6),
            "endTime": now - timedelta(days=6, hours=2),
        },
    ]

    events: List[Dict[str, Any]] = []
    bookings: List[Dict[str, Any]] = []
    contracts: List[Dict[str, Any]] = []
    measurements: List[Dict[str, Any]] = []

    for spec in event_specs:
        key = spec["key"]
        start_time = spec["startTime"]
        end_time = spec["endTime"]
        created_at = (start_time - timedelta(hours=2)).isoformat()
        accepted_at = (start_time - timedelta(hours=1)).isoformat()

        event = DREvent(
            id=DEMO_EVENT_IDS[key],
            stationId=spec["stationId"],
            pricePerKwh=spec["pricePerKwh"],
            targetEnergyKwh=spec["targetEnergyKwh"],
            maxParticipants=1,
            startTime=start_time,
            endTime=end_time,
            status=spec["status"],
            details={
                "scenario": "demo-history",
                "notes": f"Seeded {key} DR event for dashboard rehearsal",
            },
            createdAt=created_at,
        ).to_dict()
        events.append(_to_dynamo(event))

        booking = Booking(
            id=DEMO_BOOKING_IDS[key],
            userId=sarah_user_id,
            vesselId=DEMO_VESSEL_ID,
            stationId=spec["stationId"],
            startTime=start_time,
            endTime=end_time,
            status=BookingStatus.COMPLETED,
            chargerId=spec["chargerId"],
            chargerType="CCS",
        ).to_dict()
        bookings.append(_to_dynamo(booking))

        contract = Contract(
            id=DEMO_CONTRACT_IDS[key],
            bookingId=DEMO_BOOKING_IDS[key],
            vesselId=DEMO_VESSEL_ID,
            drEventId=DEMO_EVENT_IDS[key],
            vesselName="Harbor Spirit",
            energyAmount=spec["energyAmount"],
            pricePerKwh=spec["pricePerKwh"],
            totalValue=spec["energyAmount"] * spec["pricePerKwh"],
            startTime=start_time,
            endTime=end_time,
            status=ContractStatus.COMPLETED.value,
            terms=f"Seeded demo contract for {key} historical DR event.",
            committedPowerKw=max(spec["powerKw"]),
            operatorNotes="Seeded for presentation rehearsal.",
            acceptedAt=accepted_at,
            createdAt=created_at,
            updatedAt=end_time.isoformat(),
            createdBy=robert_user_id,
        ).to_dict()
        contracts.append(_to_dynamo(contract))

        interval = (end_time - start_time) / len(spec["energyKwh"])
        soc_points = [80, 68, 56, 44]
        for index, (energy_kwh, power_kw) in enumerate(
            zip(spec["energyKwh"], spec["powerKw"], strict=True)
        ):
            timestamp = start_time + (interval * index) + timedelta(minutes=15)
            measurement = Measurement(
                id=f"demo-measurement-{key}-{index + 1}",
                vesselId=DEMO_VESSEL_ID,
                contractId=DEMO_CONTRACT_IDS[key],
                drEventId=DEMO_EVENT_IDS[key],
                timestamp=timestamp,
                energyKwh=float(energy_kwh),
                powerKw=float(power_kw),
                createdAt=timestamp,
                currentSOC=float(soc_points[min(index, len(soc_points) - 1)]),
            ).to_dict()
            measurements.append(measurement)

    return events, bookings, contracts, measurements


def _collect_cleanup_targets(
    users_client: DynamoClient,
    vessels_client: DynamoClient,
    bookings_client: DynamoClient,
    contracts_client: DynamoClient,
    drevents_client: DynamoClient,
    measurements_client: DynamoClient,
    stations_client: DynamoClient,
    chargers_client: DynamoClient,
) -> MutationPlan:
    sarah_user = _find_user_by_email(users_client, SARAH_EMAIL)
    robert_user = _find_user_by_email(users_client, ROBERT_EMAIL)
    if not sarah_user or not robert_user:
        missing = []
        if not sarah_user:
            missing.append(SARAH_EMAIL)
        if not robert_user:
            missing.append(ROBERT_EMAIL)
        raise RuntimeError(f"Required demo users were not found: {', '.join(missing)}")

    sarah_user_id = str(sarah_user["id"])
    robert_user_id = str(robert_user["id"])

    sarah_vessels = _list_user_vessels(vessels_client, sarah_user_id)
    vessel_ids = {str(item.get("id") or "") for item in sarah_vessels if item.get("id")}
    vessel_ids.add(DEMO_VESSEL_ID)

    # In shared dev we want the demo reseed to fully own the operational DR tables so
    # no stale Created/Dispatched/Active records remain visible in the UI.
    contracts = contracts_client.scan_items()
    contract_ids = {
        str(item.get("id") or "")
        for item in contracts
        if str(item.get("id") or "")
    }
    contract_ids.discard("")
    dr_event_ids = {
        str(item.get("drEventId") or "")
        for item in contracts
        if str(item.get("id") or "") in contract_ids and str(item.get("drEventId") or "")
    }
    dr_event_ids.update(DEMO_EVENT_IDS.values())

    bookings = bookings_client.scan_items()
    booking_ids = {
        str(item.get("id") or "")
        for item in bookings
        if str(item.get("id") or "")
    }
    booking_ids.discard("")

    drevents = drevents_client.scan_items()
    dr_event_ids.update(
        {
            str(item.get("id") or "")
            for item in drevents
            if str(item.get("id") or "")
        }
    )
    dr_event_ids.discard("")

    measurements = measurements_client.scan_items()
    measurement_ids = {
        str(item.get("id") or "")
        for item in measurements
        if str(item.get("id") or "")
    }
    measurement_ids.discard("")

    stations = stations_client.scan_items()
    # In shared dev we want the station selector to show only the curated demo set.
    station_ids = {
        str(item.get("id") or "")
        for item in stations
        if str(item.get("id") or "")
    }
    station_ids.discard("")

    chargers = chargers_client.scan_items()
    charger_ids = {
        str(item.get("id") or "")
        for item in chargers
        if str(item.get("id") or "")
    }
    charger_ids.discard("")

    demo_stations = _build_demo_stations()
    demo_chargers = _build_demo_chargers()
    demo_vessel = _build_demo_vessel(sarah_user_id)
    demo_events, demo_bookings, demo_contracts, demo_measurements = _build_historical_records(
        sarah_user_id=sarah_user_id,
        robert_user_id=robert_user_id,
        now=datetime.now(timezone.utc),
    )

    return MutationPlan(
        deletes={
            config.MEASUREMENTS_TABLE: sorted(measurement_ids),
            config.BOOKINGS_TABLE: sorted(booking_ids),
            config.CONTRACTS_TABLE: sorted(contract_ids),
            config.DREVENTS_TABLE: sorted(dr_event_ids),
            config.CHARGERS_TABLE: sorted(charger_ids),
            config.STATIONS_TABLE: sorted(station_ids),
            config.VESSELS_TABLE: sorted(vessel_ids),
        },
        puts={
            config.STATIONS_TABLE: demo_stations,
            config.CHARGERS_TABLE: demo_chargers,
            config.VESSELS_TABLE: [demo_vessel],
            config.DREVENTS_TABLE: demo_events,
            config.BOOKINGS_TABLE: demo_bookings,
            config.CONTRACTS_TABLE: demo_contracts,
            config.MEASUREMENTS_TABLE: demo_measurements,
        },
        user_updates=[
            {
                "userId": sarah_user_id,
                "updateData": {
                    "currentVesselId": DEMO_VESSEL_ID,
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                },
            }
        ],
    )


def _print_plan(plan: MutationPlan) -> None:
    print("Demo data plan")
    print("================")
    print("Deletes:")
    for table_name, ids in plan.deletes.items():
        print(f"- {table_name}: {len(ids)} item(s)")
        for item_id in ids[:10]:
            print(f"    {item_id}")
        if len(ids) > 10:
            print(f"    ... {len(ids) - 10} more")
    print("Creates:")
    for table_name, items in plan.puts.items():
        print(f"- {table_name}: {len(items)} item(s)")
        for item in items[:10]:
            print(f"    {item.get('id')}")
        if len(items) > 10:
            print(f"    ... {len(items) - 10} more")
    print("User updates:")
    for update in plan.user_updates:
        print(f"- user {update['userId']}: {update['updateData']}")


def _apply_plan(plan: MutationPlan) -> None:
    clients = {table_name: _client(table_name) for table_name in set(plan.deletes) | set(plan.puts)}
    users_client = _client(config.USERS_TABLE)

    delete_order = [
        config.MEASUREMENTS_TABLE,
        config.BOOKINGS_TABLE,
        config.CONTRACTS_TABLE,
        config.DREVENTS_TABLE,
        config.CHARGERS_TABLE,
        config.STATIONS_TABLE,
        config.VESSELS_TABLE,
    ]
    for table_name in delete_order:
        ids = plan.deletes.get(table_name, [])
        if ids:
            for item_id in ids:
                clients[table_name].delete_item({"id": item_id})

    create_order = [
        config.STATIONS_TABLE,
        config.CHARGERS_TABLE,
        config.VESSELS_TABLE,
        config.DREVENTS_TABLE,
        config.BOOKINGS_TABLE,
        config.CONTRACTS_TABLE,
        config.MEASUREMENTS_TABLE,
    ]
    for table_name in create_order:
        items = plan.puts.get(table_name, [])
        for item in items:
            clients[table_name].put_item(_to_dynamo(item))

    for update in plan.user_updates:
        users_client.update_item(
            key={"id": update["userId"]},
            update_data=update["updateData"],
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean and reseed a safe AquaCharge demo scenario in shared dev tables."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the planned mutations. Without this flag the command runs in dry-run mode.",
    )
    args = parser.parse_args()

    if config.ENVIRONMENT.strip().lower() not in {"dev", "development"}:
        print(
            f"Refusing to run against ENVIRONMENT={config.ENVIRONMENT!r}. "
            "This command is limited to shared dev tables.",
            file=sys.stderr,
        )
        return 2

    users_client = _client(config.USERS_TABLE)
    vessels_client = _client(config.VESSELS_TABLE)
    bookings_client = _client(config.BOOKINGS_TABLE)
    contracts_client = _client(config.CONTRACTS_TABLE)
    drevents_client = _client(config.DREVENTS_TABLE)
    measurements_client = _client(config.MEASUREMENTS_TABLE)
    stations_client = _client(config.STATIONS_TABLE)
    chargers_client = _client(config.CHARGERS_TABLE)

    plan = _collect_cleanup_targets(
        users_client=users_client,
        vessels_client=vessels_client,
        bookings_client=bookings_client,
        contracts_client=contracts_client,
        drevents_client=drevents_client,
        measurements_client=measurements_client,
        stations_client=stations_client,
        chargers_client=chargers_client,
    )
    _print_plan(plan)

    if not args.apply:
        print("\nDry run only. Re-run with --apply to mutate the shared dev tables.")
        return 0

    _apply_plan(plan)
    print("\nDemo data apply complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

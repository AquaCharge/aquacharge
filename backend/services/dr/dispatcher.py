import config
from db.dynamoClient import DynamoClient
from services.battery_model.battery import BESS
from models.measurments import Measurement
from datetime import datetime, timezone
import time
from services.contracts import validation as contract_validation
from decimal import Decimal
from threading import Event


def get_dispatch_interval_seconds() -> int:
    return max(1, int(getattr(config, "DR_DISPATCH_INTERVAL_SECONDS", 60)))


def _dispatch_loop(
    event_id: str,
    valid_contracts: list[dict],
    dynamo_client: DynamoClient,
    stop_signal: Event | None = None,
):
    if stop_signal and stop_signal.is_set():
        print(f"[DR {event_id}] Stop requested before dispatch began.")
        return

    # Prepare clients for vessels and measurements
    vessels_client = DynamoClient(
        table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
    )
    measurements_client = DynamoClient(
        table_name=config.MEASUREMENTS_TABLE, region_name=config.AWS_REGION
    )

    # Build BESS instances keyed by contract id by loading the vessel record for each contract
    bess_map: dict[str, BESS] = {}
    contract_map: dict[str, dict] = {}
    for c in valid_contracts:
        contract_id = c.get("id")
        vessel_id = c.get("vesselId")
        if not contract_id or not vessel_id:
            continue
        vessel = vessels_client.get_item(key={"id": vessel_id})
        if not vessel:
            print(
                f"[DR {event_id}] Vessel record not found for contract {contract_id}, skipping."
            )
            continue
        bess_map[contract_id] = BESS(vessel)
        contract_map[contract_id] = c

    iteration = 0

    while iteration != 0 or any(not bess.at_floor for bess in bess_map.values()):
        if stop_signal and stop_signal.is_set():
            print(f"[DR {event_id}] Stop requested. Ending dispatch loop.")
            break

        iteration += 1
        now = datetime.now(timezone.utc)
        active_vessels = 0
        interval_seconds = get_dispatch_interval_seconds()
        interval_hours = interval_seconds / 3600.0

        for contract_id, bess in bess_map.items():
            if stop_signal and stop_signal.is_set():
                break

            # Skip if vessel has hit the SOC floor
            if bess.at_floor:
                continue

            active_vessels += 1

            # Calculate discharge for this interval
            transfer = bess.determine_energy_transfer(interval_hours, "discharge")
            energy_delivered = abs(transfer)  # kWh delivered to grid (positive)
            discharge_setpoint = energy_delivered / interval_hours  # kW

            # Apply transfer to in-memory battery state
            bess.apply_transfer(transfer)

            meas = Measurement(
                vesselId=bess.vessel_id,
                contractId=contract_id,
                drEventId=event_id,
                timestamp=now,
                energyKwh=energy_delivered,
                powerKw=discharge_setpoint,
                currentSOC=bess.soc_percent,
            )

            # Write measurement to measurements table
            measurements_client.put_item(meas.to_dict())

            # Persist updated SOC back to the vessel record (use Decimal for DynamoDB)
            try:
                capacity_decimal = Decimal(str(round(bess.soc, 4)))
            except Exception:
                capacity_decimal = Decimal("0")

            vessels_client.update_item(
                key={"id": bess.vessel_id},
                update_data={
                    "capacity": capacity_decimal,
                    "updatedAt": now.isoformat(),
                },
            )

            if bess.at_floor:
                print(
                    f"[DR {event_id}] Vessel {bess.vessel_id} hit SOC floor — excluded from further discharge."
                )

        # All vessels exhausted — end the loop early
        if active_vessels == 0:
            print(
                f"[DR {event_id}] All vessels at SOC floor. Ending dispatch loop early."
            )
            break

        time.sleep(interval_seconds)

    for c in valid_contracts:
        try:
            contract_validation.post_event_contract_validation(c)
        except ValueError as error:
            print(f"[DR {event_id}] Contract validation skipped: {error}")

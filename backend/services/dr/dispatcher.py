from db.dynamoClient import DynamoClient
from services.battery_model.battery import BESS
from datetime import datetime, timezone


INTERVAL_SECONDS = 5 * 60  # 5 minutes
INTERVAL_HOURS = INTERVAL_SECONDS / 3600.0


def _dispatch_loop(event_id: str, valid_contracts: list[dict], dynamo_client: DynamoClient):
    """
    Core 5-minute dispatch loop. Runs in a background thread.

    Each iteration:
      1. Skip vessels that have hit the SOC floor.
      2. Run the battery model to calculate energy transfer.
      3. Apply the transfer to the in-memory BESS state.
      4. Write an energy measurement to DynamoDB.
      5. Update the vessel's SOC in DynamoDB.

    Stops when:
      - stop_event is set (triggered by the /stop endpoint), OR
      - All vessels have hit the SOC floor.
    """

    # Build BESS instances keyed by contract id
    bess_map: dict[str, BESS] = {
        c["id"]: BESS(c["_vessel"]) for c in valid_contracts
    }
    contract_map: dict[str, dict] = {c["id"]: c for c in valid_contracts}

    # Update event status → ACTIVE
    dynamo_client.update_item(
        "DREvents",
        {"id": event_id},
        update_expr="SET #s = :s, updatedAt = :t",
        expr_names={"#s": "status"},
        expr_values={":s": "ACTIVE", ":t": datetime.now(timezone.utc).isoformat()},
    )

    iteration = 0

    while iteration != 0 or any(not bess.at_floor for bess in bess_map.values()):
        iteration += 1
        now = datetime.now(timezone.utc)
        active_vessels = 0

        for contract_id, bess in bess_map.items():
            contract = contract_map[contract_id]

            # Skip if vessel has hit the SOC floor
            if bess.at_floor:
                continue

            active_vessels += 1

            # Calculate discharge for this interval
            transfer = bess.determine_energy_transfer(INTERVAL_HOURS, "discharge")
            energy_delivered = abs(transfer)           # kWh delivered to grid (positive)
            discharge_setpoint = energy_delivered / INTERVAL_HOURS  # kW

            # Apply transfer to in-memory battery state
            bess.apply_transfer(transfer)

            # Write measurement to DynamoDB
            dynamo_client.put_item(
                "DRMeasurements",
                {
                    "id": f"{event_id}#{contract_id}#{iteration}",
                    "eventId": event_id,
                    "contractId": contract_id,
                    "timestamp": now.isoformat(),
                    "energyDelivered": round(energy_delivered, 4),  # kWh
                    "dischargeSetpoint": round(discharge_setpoint, 4),  # kW
                    "socPercent": round(bess.soc_percent, 2),  # %
                },
            )

            # Persist updated SOC back to the vessel record
            dynamo_client.update_item(
                "Vessels",
                {"id": bess.vessel_id},
                update_expr="SET currentSoc = :s, updatedAt = :t",
                expr_names={},
                expr_values={":s": round(bess.soc, 4), ":t": now.isoformat()},
            )

            if bess.at_floor:
                print(f"[DR {event_id}] Vessel {bess.vessel_id} hit SOC floor — excluded from further discharge.")

        # All vessels exhausted — end the loop early
        if active_vessels == 0:
            print(f"[DR {event_id}] All vessels at SOC floor. Ending dispatch loop early.")
            break
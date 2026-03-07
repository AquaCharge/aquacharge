"""
Seed script: add chargerType and maxCapacity to all vessel objects in the database.

- Sets sample chargerType (e.g. Type 2 AC, CCS, CHAdeMO).
- Sets sample maxCapacity (kWh); ensures capacity never exceeds maxCapacity by clamping.
- Idempotent: safe to run multiple times (updates only missing or to-be-normalized fields).

Run from backend directory:
  cd backend && python scripts/seed_vessel_attributes.py
  cd backend && python scripts/seed_vessel_attributes.py --dry-run
"""

import sys
import os

if __name__ == "__main__":
    _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    os.chdir(_backend_dir)

import decimal
from db.dynamoClient import DynamoClient


TABLE_NAME = "aquacharge-vessels-dev"
REGION = "us-east-1"

# Sample values for seeding (round-robin by index)
CHARGER_TYPES = ["Type 2 AC", "CCS", "CHAdeMO", "Type 2 AC", "CCS"]
MAX_CAPACITIES_KWH = [50.0, 100.0, 200.0, 300.0, 150.0]


def _to_decimal(n):
    if n is None:
        return decimal.Decimal("0")
    if isinstance(n, decimal.Decimal):
        return n
    return decimal.Decimal(str(n))


def seed_vessels(dry_run=False):
    client = DynamoClient(table_name=TABLE_NAME, region_name=REGION)
    items = client.scan_items()
    updated = 0
    for i, vessel in enumerate(items):
        vessel_id = vessel.get("id")
        if not vessel_id:
            continue

        capacity = _to_decimal(vessel.get("capacity", 0))
        existing_max = vessel.get("maxCapacity")
        existing_charger = vessel.get("chargerType")

        # Assign sample values when missing (or use existing)
        charger_type = existing_charger if (existing_charger and str(existing_charger).strip()) else CHARGER_TYPES[i % len(CHARGER_TYPES)]
        max_cap_val = float(existing_max) if existing_max is not None else MAX_CAPACITIES_KWH[i % len(MAX_CAPACITIES_KWH)]
        max_capacity = decimal.Decimal(str(max_cap_val))

        # Enforce capacity <= maxCapacity
        if capacity > max_capacity:
            capacity = max_capacity

        update_data = {
            "chargerType": charger_type,
            "maxCapacity": max_capacity,
            "capacity": capacity,
        }

        if dry_run:
            print(f"[dry-run] Would update vessel {vessel_id}: chargerType={charger_type}, maxCapacity={max_capacity}, capacity={capacity}")
            updated += 1
            continue

        from datetime import datetime
        update_data["updatedAt"] = datetime.now().isoformat()

        client.update_item(key={"id": vessel_id}, update_data=update_data)
        print(f"Updated vessel {vessel_id}: chargerType={charger_type}, maxCapacity={max_capacity}, capacity={capacity}")
        updated += 1

    return updated


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("Dry run: no changes will be written.")
    n = seed_vessels(dry_run=dry_run)
    print(f"Done. Processed {n} vessel(s).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AquaCharge DynamoDB Seeding Script

Populates AWS DynamoDB tables with realistic V2G platform data for development
and testing. Simulates several weeks of usage by Power Systems Operators (PSOs)
and Vessel Operators (VOs).

Usage:
    # From repo root; use backend venv for boto3 when writing to DynamoDB:
    cd backend && .venv\\Scripts\\activate && cd .. && python seed_aquacharge_db.py --aws-region us-east-1 --environment dev
    python seed_aquacharge_db.py --dry-run  # Generate data only, no write (boto3 not required)
"""

import argparse
import hashlib
import logging
import random
import sys
import time
from csv import writer as csv_writer
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Simulation anchor date (approximate "today")
SIMULATION_DATE = datetime(2025, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
PAST_WEEKS = 8
HISTORY_START = SIMULATION_DATE - timedelta(weeks=PAST_WEEKS)

# Table name pattern: aquacharge-{resource}-{environment}
TABLE_NAMES = [
    "users",
    "stations",
    "chargers",
    "vessels",
    "bookings",
    "drevents",
    "contracts",
]

# Backend uses UserRole.USER=2, ADMIN=1; UserType.VESSEL_OPERATOR=1, POWER_OPERATOR=2
USER_ROLE_USER = 2
USER_ROLE_ADMIN = 1
USER_TYPE_VO = 1
USER_TYPE_PSO = 2

# Booking status (matches backend BookingStatus enum)
BOOKING_CONFIRMED = 2   # "ACTIVE" in prompt
BOOKING_COMPLETED = 3
BOOKING_CANCELLED = 4

# Station status (matches backend StationStatus: ACTIVE=1)
STATION_ACTIVE = 1

# Charger status (matches backend ChargerStatus: ACTIVE=1, MAINTENANCE=2)
CHARGER_AVAILABLE = 1
CHARGER_MAINTENANCE = 2

# DR Event status (matches backend EventStatus string values)
DR_STATUS_CREATED = "Created"
DR_STATUS_DISPATCHED = "Dispatched"
DR_STATUS_ACTIVE = "Active"
DR_STATUS_COMPLETED = "Completed"
DR_STATUS_ARCHIVED = "Archived"

# Contract status (lowercase, matches backend ContractStatus)
CONTRACT_PENDING = "pending"
CONTRACT_ACTIVE = "active"
CONTRACT_COMPLETED = "completed"
CONTRACT_FAILED = "failed"
CONTRACT_CANCELLED = "cancelled"

LOG_FILE = "seeding_errors.log"
CREDENTIALS_CSV = "generated_user_credentials.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password with SHA-256. Optional salt for production-readiness."""
    if salt is None:
        salt = ""
    return hashlib.sha256((salt + password).encode()).hexdigest()


def generate_uuid() -> str:
    """Return a new UUID string."""
    return str(uuid4())


def get_random_datetime(
    start_date: datetime,
    end_date: datetime,
) -> datetime:
    """Return a random datetime between start_date and end_date (inclusive)."""
    delta = end_date - start_date
    sec = random.randint(0, int(delta.total_seconds()))
    return start_date + timedelta(seconds=sec)


def _ensure_decimal(value: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB; leave other types."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _ensure_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_ensure_decimal(v) for v in value]
    return value


def validate_no_double_booking(bookings: list[dict]) -> tuple[bool, list[str]]:
    """
    Ensure no two ACTIVE or COMPLETED bookings overlap on the same charger.
    Each booking must have 'chargerId', 'startTime', 'endTime', 'status'.
    Returns (valid, list of error messages).
    """
    errors = []
    # Group by chargerId
    by_charger: dict[str, list[dict]] = {}
    for b in bookings:
        if b.get("status") not in (BOOKING_CONFIRMED, BOOKING_COMPLETED):
            continue
        cid = b.get("chargerId")
        if not cid:
            errors.append(f"Booking {b.get('id')} has no chargerId")
            continue
        by_charger.setdefault(cid, []).append(b)

    for cid, blist in by_charger.items():
        blist.sort(key=lambda x: x["startTime"])
        for i in range(len(blist) - 1):
            a, b = blist[i], blist[i + 1]
            a_end = a["endTime"] if isinstance(a["endTime"], datetime) else datetime.fromisoformat(a["endTime"].replace("Z", "+00:00"))
            b_start = b["startTime"] if isinstance(b["startTime"], datetime) else datetime.fromisoformat(b["startTime"].replace("Z", "+00:00"))
            if a_end > b_start:
                errors.append(
                    f"Double-booking on charger {cid}: "
                    f"booking {a.get('id')} ends {a_end} vs {b.get('id')} starts {b_start}"
                )
    return len(errors) == 0, errors


def print_user_credentials(
    users: list[dict],
    credentials_list: list[dict],
    csv_path: str,
) -> None:
    """Print credentials to console and write to CSV."""
    vo_users = [u for u in credentials_list if u.get("type") == "VO"]
    pso_users = [u for u in credentials_list if u.get("type") == "PSO"]
    logger.info("========== USER CREDENTIALS ==========")
    logger.info("VESSEL OPERATORS (VO):")
    for u in vo_users:
        logger.info("  Email: %s | Password: %s", u["email"], u["password"])
    logger.info("POWER SYSTEM OPERATORS (PSO):")
    for u in pso_users:
        logger.info("  Email: %s | Password: %s", u["email"], u["password"])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv_writer(f)
        w.writerow(["User_Type", "Email", "Password", "Role", "Organization", "Created_Date"])
        for u in credentials_list:
            w.writerow([
                u["type"],
                u["email"],
                u["password"],
                u["role"],
                u.get("organization", ""),
                u.get("created_date", ""),
            ])
    logger.info("Credentials saved to: %s", csv_path)


# -----------------------------------------------------------------------------
# Data Generation Functions
# -----------------------------------------------------------------------------


def generate_users() -> tuple[list[dict], list[dict]]:
    """
    Create 14 users: 10 VO users, 1 VO admin, 3 PSO users.
    Returns (list of user dicts for DB, list of credentials for CSV).
    """
    vo_orgs = [
        ("org-atlantic-marine", "Atlantic Marine Corp"),
        ("org-bay-shipping", "Bay Shipping Co"),
        ("org-nb-ferries", "NB Ferries Ltd"),
    ]
    pso_org = ("org-maritime-grid", "Maritime Grid Operator")

    first_names_vo = [
        "James", "Sarah", "Michael", "Emma", "David", "Olivia",
        "Robert", "Sophie", "William", "Anna", "Thomas",
    ]
    last_names_vo = [
        "Morrison", "Chen", "O'Brien", "Lévesque", "MacDonald",
        "Kim", "Wilson", "Taylor", "Brown", "Davis", "Admin",
    ]
    companies_vo = ["atlanticmarine.com", "bayshipping.com", "nbferries.com"]

    first_names_pso = ["Robert", "Jennifer", "Daniel"]
    last_names_pso = ["Wilson", "Martinez", "Thompson"]
    company_pso = "gridoperator.com"

    passwords_vo = ["VesselOp@2024", "ShipMgr#2024", "Maritime@2024", "HarborOp#2024", "Crew2024!"]
    passwords_pso = ["GridOp@2024", "GridMgr#2024", "PSO@2024"]
    admin_password = "AdminPass@2024"

    users = []
    credentials_list = []

    # 10 VO users + 1 VO admin
    for i in range(11):
        is_admin = i == 10
        first = first_names_vo[i % len(first_names_vo)]
        last = last_names_vo[i % len(last_names_vo)]
        org_id, org_name = vo_orgs[i % len(vo_orgs)]
        company = companies_vo[i % len(companies_vo)]
        email = f"{first.lower()}.{last.lower().replace(' ', '')}@{company}".replace("'", "")
        if is_admin:
            email = f"admin@{company}"
            display = "VO Admin"
            password = admin_password
            role = USER_ROLE_ADMIN
        else:
            display = f"{first} {last}"
            password = random.choice(passwords_vo)
            role = USER_ROLE_USER

        created = get_random_datetime(HISTORY_START, SIMULATION_DATE)
        updated = get_random_datetime(created, SIMULATION_DATE)

        u = {
            "id": generate_uuid(),
            "orgId": org_id,
            "displayName": display,
            "email": email,
            "passwordHash": hash_password(password),
            "role": role,
            "type": USER_TYPE_VO,
            "active": True,
            "createdAt": created.isoformat(),
            "updatedAt": updated.isoformat(),
        }
        users.append(u)
        credentials_list.append({
            "type": "VO",
            "email": email,
            "password": password,
            "role": "Admin" if is_admin else "User",
            "organization": org_name,
            "created_date": created.date().isoformat(),
        })

    # 3 PSO users
    for i in range(3):
        first = first_names_pso[i]
        last = last_names_pso[i]
        email = f"{first.lower()}.{last.lower()}@{company_pso}"
        display = f"{first} {last}"
        password = passwords_pso[i]
        created = get_random_datetime(HISTORY_START, SIMULATION_DATE)
        updated = get_random_datetime(created, SIMULATION_DATE)
        u = {
            "id": generate_uuid(),
            "orgId": pso_org[0],
            "displayName": display,
            "email": email,
            "passwordHash": hash_password(password),
            "role": USER_ROLE_USER,
            "type": USER_TYPE_PSO,
            "active": True,
            "createdAt": created.isoformat(),
            "updatedAt": updated.isoformat(),
        }
        users.append(u)
        credentials_list.append({
            "type": "PSO",
            "email": email,
            "password": password,
            "role": "User",
            "organization": pso_org[1],
            "created_date": created.date().isoformat(),
        })

    return users, credentials_list


def generate_stations() -> list[dict]:
    """Create 4 stations with real New Brunswick port coordinates."""
    stations_data = [
        ("Canaport", "Saint John", 45.2159, -65.9786),
        ("Port of Belledune", "Belledune", 47.9027, -65.8475),
        ("Port of Saint John", "Saint John", 45.2539, -66.0321),
        ("Saint John Harbour", "Saint John", 45.2539, -66.0321),
    ]
    stations = []
    for display_name, city, lat, lon in stations_data:
        stations.append({
            "id": generate_uuid(),
            "displayName": display_name,
            "country": "Canada",
            "provinceOrState": "NB",
            "city": city,
            "longitude": Decimal(str(lon)),
            "latitude": Decimal(str(lat)),
            "status": STATION_ACTIVE,
        })
    return stations


def generate_chargers(stations: list[dict]) -> list[dict]:
    """Create 5-10 chargers per station (28-40 total). 70% bidirectional, 95% available."""
    rates = [10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]
    chargers = []
    for station in stations:
        n = random.randint(5, 10)
        for _ in range(n):
            charger_type = "bidirectional" if random.random() < 0.70 else "unidirectional"
            max_rate = random.choice(rates)
            status = CHARGER_MAINTENANCE if random.random() < 0.05 else CHARGER_AVAILABLE
            chargers.append({
                "id": generate_uuid(),
                "chargingStationId": station["id"],
                "chargerType": charger_type,
                "maxRate": Decimal(str(max_rate)),
                "status": status,
            })
    return chargers


def generate_vessels(
    vo_users: list[dict],
) -> list[dict]:
    """
    Create 14-24 vessels, 1-5 per VO user (1-2 most common).
    Only VO users (type=1) own vessels.
    """
    vessel_names = [
        "Nordic Wind", "Atlantic Wave", "Bay Guardian", "Fundy Spirit",
        "Saint John Star", "Belledune Runner", "Harbour Mist", "Coastal Dawn",
        "Maritime Pride", "Bay Runner", "Tide Master", "Harbour Light",
        "Atlantic Breeze", "Fundy Queen", "Coastal Spirit", "Nordic Tide",
        "Bay Explorer", "Harbour Star", "Maritime Dawn", "Atlantic Guardian",
    ]
    vessel_types = [
        "electric_cargo",
        "electric_container",
        "electric_ferry",
        "electric_tanker",
    ]
    # NB area for vessel locations (around the 4 ports)
    locations = [
        (45.25, -66.03),
        (45.22, -65.98),
        (47.90, -65.85),
        (45.26, -66.04),
        (45.20, -66.00),
        (47.88, -65.82),
    ]

    vessels = []
    names_used = set()
    # Distribution: most users get 1-2 vessels, a few get 3-5
    counts_per_user = []
    for _ in vo_users:
        r = random.random()
        if r < 0.5:
            counts_per_user.append(1)
        elif r < 0.85:
            counts_per_user.append(2)
        elif r < 0.95:
            counts_per_user.append(random.randint(3, 4))
        else:
            counts_per_user.append(5)
    total_target = random.randint(14, 24)
    # Adjust so total is in range
    current_total = sum(counts_per_user)
    while current_total < 14:
        i = random.randint(0, len(counts_per_user) - 1)
        counts_per_user[i] = min(counts_per_user[i] + 1, 5)
        current_total = sum(counts_per_user)
    while current_total > 24:
        i = random.randint(0, len(counts_per_user) - 1)
        if counts_per_user[i] > 1:
            counts_per_user[i] -= 1
            current_total = sum(counts_per_user)
        else:
            break

    vessel_idx = 0
    for user, count in zip(vo_users, counts_per_user):
        for _ in range(count):
            name = random.choice(vessel_names)
            while name in names_used and len(names_used) < len(vessel_names):
                name = random.choice(vessel_names)
            names_used.add(name)

            capacity = random.uniform(100.0, 500.0)
            rate = random.uniform(5.0, 30.0)
            consumption = 0.002  # kWh per km
            range_meters = capacity / consumption
            range_meters = max(50000, min(200000, range_meters))

            lat, lon = random.choice(locations)
            lat += random.uniform(-0.05, 0.05)
            lon += random.uniform(-0.05, 0.05)

            created = get_random_datetime(HISTORY_START, SIMULATION_DATE)
            updated = get_random_datetime(SIMULATION_DATE - timedelta(days=14), SIMULATION_DATE)

            vessels.append({
                "id": generate_uuid(),
                "userId": user["id"],
                "displayName": name,
                "vesselType": random.choice(vessel_types),
                "capacity": capacity,
                "maxChargeRate": rate,
                "minChargeRate": Decimal("0"),
                "maxDischargeRate": rate,
                "rangeMeters": range_meters,
                "active": True,
                "longitude": lon,
                "latitude": lat,
                "createdAt": created.isoformat(),
                "updatedAt": updated.isoformat(),
            })
            vessel_idx += 1

    return vessels


def generate_bookings(
    vo_users: list[dict],
    vessels: list[dict],
    stations: list[dict],
    chargers: list[dict],
) -> list[dict]:
    """
    Create 30-50 bookings. No double-booking on same charger.
    Status: 60% COMPLETED, 30% ACTIVE (CONFIRMED), 10% CANCELLED.
    """
    # Build list of chargers per station (available for booking)
    chargers_by_station: dict[str, list[dict]] = {}
    for c in chargers:
        if c["status"] != CHARGER_AVAILABLE:
            continue
        sid = c["chargingStationId"]
        chargers_by_station.setdefault(sid, []).append(c)

    vessel_by_id = {v["id"]: v for v in vessels}
    vo_user_ids = {u["id"] for u in vo_users}
    vessels_by_user: dict[str, list[dict]] = {}
    for v in vessels:
        if v["userId"] in vo_user_ids:
            vessels_by_user.setdefault(v["userId"], []).append(v)

    num_bookings = random.randint(30, 50)
    bookings = []
    # Per-charger list of (start, end) for conflict check
    charger_slots: dict[str, list[tuple[datetime, datetime]]] = {}

    def overlaps(s1: datetime, e1: datetime, s2: datetime, e2: datetime) -> bool:
        return not (e1 <= s2 or e2 <= s1)

    def find_slot(charger_id: str, duration_hours: float, status_kind: str) -> tuple[Optional[datetime], Optional[datetime]]:
        # status_kind: "completed" (past), "active" (recent/future), "cancelled" (any)
        slots = charger_slots.get(charger_id, [])
        for _ in range(100):
            if status_kind == "completed":
                start = get_random_datetime(HISTORY_START, SIMULATION_DATE - timedelta(days=7))
            elif status_kind == "active":
                start = get_random_datetime(SIMULATION_DATE - timedelta(days=7), SIMULATION_DATE + timedelta(days=7))
            else:
                start = get_random_datetime(HISTORY_START, SIMULATION_DATE + timedelta(days=3))
            end = start + timedelta(hours=duration_hours)
            if end > SIMULATION_DATE + timedelta(days=14):
                continue
            conflict = False
            for (s, e) in slots:
                if overlaps(start, end, s, e):
                    conflict = True
                    break
            if not conflict:
                return start, end
        return None, None

    status_choices = (
        [BOOKING_COMPLETED] * 60 +
        [BOOKING_CONFIRMED] * 30 +
        [BOOKING_CANCELLED] * 10
    )
    random.shuffle(status_choices)

    created_count = 0
    for i in range(num_bookings):
        status = status_choices[i % len(status_choices)]
        status_kind = "completed" if status == BOOKING_COMPLETED else ("active" if status == BOOKING_CONFIRMED else "cancelled")

        user = random.choice(vo_users)
        user_vessels = vessels_by_user.get(user["id"], [])
        if not user_vessels:
            continue
        vessel = random.choice(user_vessels)
        station = random.choice(stations)
        station_chargers = chargers_by_station.get(station["id"], [])
        if not station_chargers:
            continue
        charger = random.choice(station_chargers)
        duration_hours = random.uniform(2, 8)
        start, end = find_slot(charger["id"], duration_hours, status_kind)
        if start is None or end is None:
            continue

        charger_slots.setdefault(charger["id"], []).append((start, end))
        created = get_random_datetime(HISTORY_START, start)
        bookings.append({
            "id": generate_uuid(),
            "userId": user["id"],
            "vesselId": vessel["id"],
            "stationId": station["id"],
            "chargerId": charger["id"],
            "chargerType": charger["chargerType"],
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "status": status,
            "createdAt": created.isoformat(),
        })
        created_count += 1

    return bookings


def generate_dr_events(stations: list[dict]) -> list[dict]:
    """Create 8-12 DR events. createdAt 30-120 min before startTime."""
    n = random.randint(8, 12)
    statuses = (
        [DR_STATUS_COMPLETED] * 50 +
        [DR_STATUS_ACTIVE] * 15 +
        [DR_STATUS_ARCHIVED] * 15 +
        [DR_STATUS_CREATED] * 10 +
        [DR_STATUS_DISPATCHED] * 10
    )
    events = []
    for _ in range(n):
        station = random.choice(stations)
        start = get_random_datetime(HISTORY_START, SIMULATION_DATE + timedelta(days=7))
        duration_hours = random.uniform(1, 4)
        end = start + timedelta(hours=duration_hours)
        created_offset_min = random.randint(30, 120)
        created = start - timedelta(minutes=created_offset_min)

        status = random.choice(statuses)
        events.append({
            "id": generate_uuid(),
            "stationId": station["id"],
            "targetEnergyKwh": round(random.uniform(100.0, 1000.0), 1),
            "pricePerKwh": round(random.uniform(0.05, 0.20), 2),
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "maxParticipants": random.randint(3, 15),
            "status": status,
            "createdAt": created.isoformat(),
        })
    return events


def generate_contracts(
    dr_events: list[dict],
    bookings: list[dict],
    pso_users: list[dict],
    vessels: list[dict],
) -> list[dict]:
    """
    Create 40-60 contracts. At least one of each status.
    All createdBy must be PSO users. Some bookingId can be null.
    """
    vessel_by_id = {v["id"]: v for v in vessels}
    booking_by_id = {b["id"]: b for b in bookings if b.get("status") != BOOKING_CANCELLED}
    # Completed/active bookings that have a vessel and time range
    good_bookings = [b for b in bookings if b.get("status") in (BOOKING_COMPLETED, BOOKING_CONFIRMED)]

    status_counts = {
        CONTRACT_PENDING: random.randint(5, 8),
        CONTRACT_COMPLETED: random.randint(15, 25),
        CONTRACT_ACTIVE: random.randint(3, 6),
        CONTRACT_FAILED: random.randint(1, 3),
        CONTRACT_CANCELLED: random.randint(2, 5),
    }
    total = min(60, max(40, sum(status_counts.values())))
    # Ensure at least 1 of each
    for k in status_counts:
        if status_counts[k] < 1:
            status_counts[k] = 1
    # Trim or pad to total
    current = sum(status_counts.values())
    if current > total:
        for _ in range(current - total):
            k = max(status_counts, key=status_counts.get)
            if status_counts[k] > 1:
                status_counts[k] -= 1
    elif current < total:
        status_counts[CONTRACT_COMPLETED] += total - current

    contracts = []
    for status, count in status_counts.items():
        for _ in range(count):
            dr = random.choice(dr_events)
            pso = random.choice(pso_users)
            # Link to booking when possible (for completed/active contracts often)
            booking = None
            if good_bookings and status in (CONTRACT_ACTIVE, CONTRACT_COMPLETED) and random.random() < 0.8:
                booking = random.choice(good_bookings)
            elif good_bookings and status == CONTRACT_PENDING and random.random() < 0.5:
                booking = random.choice(good_bookings)

            if booking:
                vessel_id = booking["vesselId"]
                vessel_name = vessel_by_id.get(vessel_id, {}).get("displayName", "Unknown Vessel")
                booking_id = booking["id"]
                start = datetime.fromisoformat(booking["startTime"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(booking["endTime"].replace("Z", "+00:00"))
            else:
                vessel_id = random.choice(vessels)["id"] if vessels else ""
                vessel_name = vessel_by_id.get(vessel_id, {}).get("displayName", "Placeholder Vessel") if vessel_id else "Placeholder Vessel"
                booking_id = ""
                start = datetime.fromisoformat(dr["startTime"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(dr["endTime"].replace("Z", "+00:00"))

            energy = round(random.uniform(20.0, 300.0), 1)
            price = round(random.uniform(0.05, 0.20), 2)
            total_value = round(energy * price, 2)
            created = get_random_datetime(HISTORY_START, start)
            updated_end = max(start, min(end, SIMULATION_DATE))
            updated = get_random_datetime(start, updated_end)

            contracts.append({
                "id": generate_uuid(),
                "bookingId": booking_id,
                "vesselId": vessel_id,
                "drEventId": dr["id"],
                "vesselName": vessel_name,
                "energyAmount": energy,
                "pricePerKwh": price,
                "totalValue": total_value,
                "startTime": start.isoformat(),
                "endTime": end.isoformat(),
                "status": status,
                "terms": "Seed contract terms for V2G participation.",
                "createdAt": created.isoformat(),
                "updatedAt": updated.isoformat(),
                "createdBy": pso["id"],
            })

    return contracts


# -----------------------------------------------------------------------------
# Database Population
# -----------------------------------------------------------------------------


# Tables required to exist (drevents optional if not yet deployed)
REQUIRED_TABLES = ["users", "stations", "chargers", "vessels", "bookings", "contracts"]


def verify_database_connection(region: str, env: str) -> bool:
    """Check AWS credentials and that required tables exist."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        dynamodb = boto3.resource("dynamodb", region_name=region)
        for name in REQUIRED_TABLES:
            table_name = f"aquacharge-{name}-{env}"
            table = dynamodb.Table(table_name)
            table.load()
    except NoCredentialsError:
        logger.error("AWS credentials not configured. Configure ~/.aws/credentials or env vars.")
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.error("Table not found: %s", table_name)
        else:
            logger.error("DynamoDB error: %s", e)
        return False
    return True


def write_to_dynamodb(
    table_name: str,
    items: list[dict],
    region: str,
    dry_run: bool = False,
) -> tuple[int, list[dict]]:
    """
    Batch write items to DynamoDB. Converts floats to Decimal.
    Returns (success_count, unprocessed_items).
    """
    if dry_run or not items:
        return len(items), []

    import boto3
    from botocore.exceptions import ClientError
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    converted = [_ensure_decimal(item) for item in items]
    success_count = 0
    with table.batch_writer() as writer:
        for item in converted:
            try:
                writer.put_item(Item=item)
                success_count += 1
            except ClientError as e:
                if e.response["Error"]["Code"] == "ValidationException":
                    # Decimal/long might need conversion
                    fix = {k: (int(v) if isinstance(v, Decimal) and v == int(v) else v) for k, v in item.items()}
                    writer.put_item(Item=fix)
                    success_count += 1
                else:
                    raise
    return success_count, []


def seed_database(
    all_data: dict,
    region: str,
    env: str,
    dry_run: bool = False,
) -> bool:
    """Write all generated data to DynamoDB tables."""
    table_resources = [
        ("users", "users"),
        ("stations", "stations"),
        ("chargers", "chargers"),
        ("vessels", "vessels"),
        ("bookings", "bookings"),
        ("drevents", "drevents"),
        ("contracts", "contracts"),
    ]
    for key, tname in table_resources:
        items = all_data.get(key, [])
        full_name = f"aquacharge-{tname}-{env}"
        try:
            count, unproc = write_to_dynamodb(full_name, items, region, dry_run=dry_run)
            if dry_run:
                logger.info("[dry-run] %s: would write %d records", full_name, len(items))
            else:
                logger.info("[OK] %s: %d records written", full_name, count)
                if unproc:
                    logger.warning("  Unprocessed: %d", len(unproc))
        except Exception as e:
            from botocore.exceptions import ClientError
            if isinstance(e, ClientError) and e.response["Error"]["Code"] == "ResourceNotFoundException" and key == "drevents":
                logger.warning(
                    "DREvents table %s not found; skipping. Create aquacharge-drevents-%s to seed DR events.",
                    full_name,
                    env,
                )
            else:
                logger.exception("Write failed for %s: %s", full_name, e)
                return False
    return True


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed AquaCharge DynamoDB tables")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region")
    parser.add_argument("--environment", default="dev", help="Environment (dev, staging, prod)")
    parser.add_argument("--confirm-delete", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="Generate data but do not write to DynamoDB")
    args = parser.parse_args()

    logger.info("========== AquaCharge Database Seeding ==========\n")

    if not args.dry_run and not args.confirm_delete:
        try:
            ans = input("WARNING: This will seed/overwrite DynamoDB tables. Continue? (y/n): ")
            if ans.strip().lower() != "y":
                logger.info("Aborted.")
                return 0
        except EOFError:
            return 1

    # Generate data
    logger.info("[1/7] Generating Users...")
    users, credentials_list = generate_users()
    logger.info("  OK %d users created", len(users))

    logger.info("[2/7] Generating Stations...")
    stations = generate_stations()
    logger.info("  OK %d stations created", len(stations))

    logger.info("[3/7] Generating Chargers...")
    chargers = generate_chargers(stations)
    logger.info("  OK %d chargers created", len(chargers))

    vo_users = [u for u in users if u["type"] == USER_TYPE_VO]
    pso_users = [u for u in users if u["type"] == USER_TYPE_PSO]

    logger.info("[4/7] Generating Vessels...")
    vessels = generate_vessels(vo_users)
    logger.info("  OK %d vessels created", len(vessels))

    logger.info("[5/7] Generating Bookings...")
    bookings = generate_bookings(vo_users, vessels, stations, chargers)
    logger.info("  OK %d bookings created", len(bookings))

    ok, errs = validate_no_double_booking(bookings)
    if not ok:
        for e in errs:
            logger.error("  %s", e)
        logger.error("Validation failed: double-booking or missing chargerId.")
        return 1
    logger.info("  OK No double-booking conflicts")

    logger.info("[6/7] Generating DR Events...")
    dr_events = generate_dr_events(stations)
    logger.info("  OK %d DR events created", len(dr_events))

    logger.info("[7/7] Generating Contracts...")
    contracts = generate_contracts(dr_events, bookings, pso_users, vessels)
    logger.info("  OK %d contracts created", len(contracts))

    # Foreign key checks (id references)
    station_ids = {s["id"] for s in stations}
    user_ids = {u["id"] for u in users}
    vessel_ids = {v["id"] for v in vessels}
    booking_ids = {b["id"] for b in bookings}
    dr_ids = {e["id"] for e in dr_events}
    for b in bookings:
        if b["stationId"] not in station_ids or b["userId"] not in user_ids or b["vesselId"] not in vessel_ids:
            logger.error("Booking %s has invalid foreign key", b["id"])
            return 1
    for c in contracts:
        if c["drEventId"] not in dr_ids or c["createdBy"] not in user_ids:
            logger.error("Contract %s has invalid foreign key", c["id"])
            return 1

    logger.info("\nValidation Results:")
    logger.info("  OK No double-booking conflicts")
    logger.info("  OK All foreign keys valid")

    all_data = {
        "users": users,
        "stations": stations,
        "chargers": chargers,
        "vessels": vessels,
        "bookings": bookings,
        "drevents": dr_events,
        "contracts": contracts,
    }

    if not args.dry_run:
        if not verify_database_connection(args.aws_region, args.environment):
            logger.error("Database verification failed. Aborting.")
            return 1

    logger.info("\nWriting to DynamoDB...")
    if not seed_database(all_data, args.aws_region, args.environment, dry_run=args.dry_run):
        return 1

    print_user_credentials(users, credentials_list, CREDENTIALS_CSV)

    logger.info("\n========== COMPLETION ==========")
    logger.info("OK Database seeding completed successfully")
    logger.info("OK Credentials saved to: ./%s", CREDENTIALS_CSV)
    logger.info("WARNING: IMPORTANT: Secure credentials file before deployment")
    return 0


if __name__ == "__main__":
    sys.exit(main())

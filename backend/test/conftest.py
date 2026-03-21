import hashlib
import os
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

import config

# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------
_TABLE_DEFINITIONS = [
    {
        "name": config.USERS_TABLE,
        "extra_attrs": [{"AttributeName": "email", "AttributeType": "S"}],
        "gsis": [
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    {
        "name": config.VESSELS_TABLE,
        "extra_attrs": [{"AttributeName": "userId", "AttributeType": "S"}],
        "gsis": [
            {
                "IndexName": "userId-index",
                "KeySchema": [{"AttributeName": "userId", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    {"name": config.BOOKINGS_TABLE},
    {"name": config.CHARGERS_TABLE},
    {"name": config.STATIONS_TABLE},
    {"name": config.CONTRACTS_TABLE},
    {"name": config.DREVENTS_TABLE},
    {"name": config.MEASUREMENTS_TABLE},
    {"name": config.PORTS_TABLE},
    {"name": config.ORGS_TABLE},
]

# Seed data required by tests that assume pre-existing records
_SEED_USERS = [
    {
        "id": "admin-seed-001",
        "displayName": "Admin Jason",
        "email": "admin.jason@boats.com",
        "passwordHash": hashlib.sha256("BoatAdmin#3232".encode()).hexdigest(),
        "role": 1,
        "type": 2,
        "active": True,
        "createdAt": "2024-01-01T00:00:00",
    }
]

_SEED_CHARGERS = [
    {
        "id": "charger-seed-001",
        "chargingStationId": "station-001",
        "chargerType": "Type 2 AC",
        "maxRate": "22.0",
        "status": "active",
    }
]

_SEED_VESSELS = [
    {
        "id": "vessel-seed-001",
        "userId": "admin-seed-001",
        "displayName": "Seed Vessel",
        "vesselType": "ferry",
        "chargerType": "Type 2 AC",
        "capacity": Decimal("50"),
        "maxCapacity": Decimal("100"),
        "active": True,
        "createdAt": "2024-01-01T00:00:00",
    }
]


@pytest.fixture(autouse=True)
def mock_dynamo():
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)

        for table_def in _TABLE_DEFINITIONS:
            attr_defs = [{"AttributeName": "id", "AttributeType": "S"}]
            attr_defs += table_def.get("extra_attrs", [])

            kwargs = {
                "TableName": table_def["name"],
                "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
                "AttributeDefinitions": attr_defs,
                "BillingMode": "PAY_PER_REQUEST",
            }
            if table_def.get("gsis"):
                kwargs["GlobalSecondaryIndexes"] = table_def["gsis"]

            dynamodb.create_table(**kwargs)

        # Seed records needed by tests that assume pre-existing data
        users_table = dynamodb.Table(config.USERS_TABLE)
        for user in _SEED_USERS:
            users_table.put_item(Item=user)

        chargers_table = dynamodb.Table(config.CHARGERS_TABLE)
        for charger in _SEED_CHARGERS:
            chargers_table.put_item(Item=charger)

        vessels_table = dynamodb.Table(config.VESSELS_TABLE)
        for vessel in _SEED_VESSELS:
            vessels_table.put_item(Item=vessel)

        yield

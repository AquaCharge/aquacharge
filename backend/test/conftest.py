import hashlib
import os
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

import config

# ---------------------------------------------------------------------------
# Table definitions — mirrors infra/lib/dynamodb-tables.ts exactly
# Each entry: name, extra_attrs (beyond "id"), gsis
# ---------------------------------------------------------------------------
_S = "S"
_N = "N"


def _gsi(name, pk, pk_type=_S, sk=None, sk_type=_S):
    schema = [{"AttributeName": pk, "KeyType": "HASH"}]
    attrs = [{"AttributeName": pk, "AttributeType": pk_type}]
    if sk:
        schema.append({"AttributeName": sk, "KeyType": "RANGE"})
        attrs.append({"AttributeName": sk, "AttributeType": sk_type})
    return {"index": {"IndexName": name, "KeySchema": schema, "Projection": {"ProjectionType": "ALL"}}, "attrs": attrs}


_TABLE_DEFINITIONS = [
    {
        "name": config.USERS_TABLE,
        "gsis": [
            _gsi("email-index", "email"),
            _gsi("orgId-index", "orgId"),
        ],
    },
    {
        "name": config.STATIONS_TABLE,
        "gsis": [
            _gsi("city-index", "city", sk="provinceOrState"),
            _gsi("status-index", "status", pk_type=_N),
        ],
    },
    {
        "name": config.CHARGERS_TABLE,
        "gsis": [
            _gsi("chargingStationId-index", "chargingStationId"),
            _gsi("chargerType-index", "chargerType"),
        ],
    },
    {
        "name": config.VESSELS_TABLE,
        "gsis": [
            _gsi("userId-index", "userId"),
            _gsi("vesselType-index", "vesselType"),
        ],
    },
    {
        "name": config.BOOKINGS_TABLE,
        "gsis": [
            _gsi("userId-index", "userId", sk="startTime"),
            _gsi("stationId-index", "stationId", sk="startTime"),
            _gsi("vesselId-index", "vesselId", sk="startTime"),
            _gsi("status-index", "status", pk_type=_N, sk="startTime"),
        ],
    },
    {
        "name": config.CONTRACTS_TABLE,
        "gsis": [
            _gsi("bookingId-index", "bookingId"),
            _gsi("vesselId-index", "vesselId"),
            _gsi("drEventId-index", "drEventId"),
            _gsi("status-index", "status", sk="startTime"),
            _gsi("createdBy-index", "createdBy", sk="createdAt"),
        ],
    },
    {
        "name": config.DREVENTS_TABLE,
        "gsis": [
            _gsi("stationId-index", "stationId", sk="startTime"),
            _gsi("status-index", "status", sk="startTime"),
            _gsi("startTime-index", "startTime"),
        ],
    },
    {
        "name": config.ORGS_TABLE,
        "gsis": [
            _gsi("displayName-index", "displayName"),
        ],
    },
    {
        "name": config.MEASUREMENTS_TABLE,
        "gsis": [
            _gsi("contractId-index", "contractId"),
            _gsi("drEventId-index", "drEventId"),
            _gsi("vesselId-index", "vesselId"),
        ],
    },
    {"name": config.PORTS_TABLE, "gsis": []},
]

# ---------------------------------------------------------------------------
# Seed data — records assumed to exist by tests using real table queries
# ---------------------------------------------------------------------------
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
            # Collect all attribute definitions (id + GSI keys, deduplicated)
            attr_map = {"id": "S"}
            gsi_list = []
            for g in table_def.get("gsis", []):
                gsi_list.append(g["index"])
                for attr in g["attrs"]:
                    attr_map[attr["AttributeName"]] = attr["AttributeType"]

            attr_defs = [
                {"AttributeName": k, "AttributeType": v} for k, v in attr_map.items()
            ]

            kwargs = {
                "TableName": table_def["name"],
                "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
                "AttributeDefinitions": attr_defs,
                "BillingMode": "PAY_PER_REQUEST",
            }
            if gsi_list:
                kwargs["GlobalSecondaryIndexes"] = gsi_list

            dynamodb.create_table(**kwargs)

        # Seed records needed by tests that assume pre-existing data
        dynamodb.Table(config.USERS_TABLE).put_item(Item=_SEED_USERS[0])
        dynamodb.Table(config.CHARGERS_TABLE).put_item(Item=_SEED_CHARGERS[0])
        dynamodb.Table(config.VESSELS_TABLE).put_item(Item=_SEED_VESSELS[0])

        yield

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

TABLE_NAME = "aquacharge-ports-dev"
DEFAULT_REGION = "us-east-1"
REQUIRED_FIELDS = ["portId", "CITY", "STATE", "COUNTRY", "LATITUDE", "LONGITUDE"]
PROGRESS_INTERVAL = 500


def load_env_vars(env_path: Path) -> Dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(dotenv_path=env_path)

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", DEFAULT_REGION)

    missing = [
        name
        for name, value in [
            ("AWS_ACCESS_KEY_ID", access_key),
            ("AWS_SECRET_ACCESS_KEY", secret_key),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region": region,
    }


def get_dynamodb_table(credentials: Dict[str, str]):
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=credentials["region"],
        aws_access_key_id=credentials["aws_access_key_id"],
        aws_secret_access_key=credentials["aws_secret_access_key"],
    )
    return dynamodb.Table(TABLE_NAME)


def load_ports_json(json_path: Path) -> List[Dict]:
    if not json_path.exists():
        raise FileNotFoundError(f"Ports file not found at {json_path}")
    with json_path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    if not isinstance(data, list):
        raise ValueError("Ports JSON is not a list")
    return data


def filter_valid_ports(raw_ports: List[Dict]) -> List[Dict]:
    valid_ports: List[Dict] = []
    for index, port in enumerate(raw_ports):
        missing_fields = [field for field in REQUIRED_FIELDS if field not in port or port[field] is None]
        if missing_fields:
            print(f"Warning: port at index {index} missing fields {missing_fields}; skipping.")
            continue
        valid_ports.append(port)
    return valid_ports


def write_ports_to_dynamo(table, ports: List[Dict]) -> int:
    written = 0
    total = len(ports)
    with table.batch_writer(overwrite_by_pkeys=["portId"]) as batch:
        for idx, port in enumerate(ports, start=1):
            batch.put_item(
                Item={
                    "portId": port["portId"],
                    "CITY": port["CITY"],
                    "STATE": port["STATE"],
                    "COUNTRY": port["COUNTRY"],
                    "LATITUDE": Decimal(str(port["LATITUDE"])),
                    "LONGITUDE": Decimal(str(port["LONGITUDE"])),
                }
            )
            written += 1
            if PROGRESS_INTERVAL and idx % PROGRESS_INTERVAL == 0:
                print(f"Wrote {idx}/{total} ports to DynamoDB...")
    return written


def main() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    env_path = backend_root / ".env"
    ports_json_path = backend_root / "data" / "ports_with_ids.json"

    try:
        credentials = load_env_vars(env_path)
        raw_ports = load_ports_json(ports_json_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"Loaded {len(raw_ports)} ports from JSON.")
    ports_to_write = filter_valid_ports(raw_ports)

    if not ports_to_write:
        print("No valid ports to write; exiting.")
        sys.exit(0)

    try:
        table = get_dynamodb_table(credentials)
        written_count = write_ports_to_dynamo(table, ports_to_write)
    except (BotoCoreError, ClientError) as exc:
        print(f"Error writing to DynamoDB: {exc}")
        sys.exit(1)

    print(f"Successfully wrote {written_count} ports to DynamoDB table '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict

import boto3
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables early so services can rely on them.
load_dotenv(ENV_PATH)

PORTS_TABLE_NAME = "aquacharge-ports-dev"


class MissingAWSCredentials(RuntimeError):
    """Raised when required AWS credentials are missing."""


def _get_aws_settings() -> Dict[str, str]:
    access_key = os.getenv("AWS_ACCESS_KEY")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        raise MissingAWSCredentials(
            "AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY must be set in backend/.env"
        )

    return {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region_name": region,
    }


@lru_cache()
def get_dynamodb_resource():
    settings = _get_aws_settings()
    return boto3.resource("dynamodb", **settings)


@lru_cache()
def get_ports_table():
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(PORTS_TABLE_NAME)

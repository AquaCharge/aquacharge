
from decimal import Decimal

from models.vessel import Vessel
from db.dynamoClient import DynamoClient
from models import contract
from boto3.dynamodb.conditions import Key


MAX_FAILED_CONTRACTS = 3
MIN_FULFILLMENT_RATE = 0.75
KW_TOLERANCE = 0.10


_contracts_client = DynamoClient(table_name="aquacharge-contracts-dev", region_name="us-east-1")
_measurements_client = DynamoClient(table_name="aquacharge-measurements-dev", region_name="us-east-1")


def pre_event_contract_validation(vessel: Vessel) -> bool:

    past_contracts = _contracts_client.query_gsi(
        index_name="vesselId-index",
        key_condition_expression=Key("vesselId").eq(vessel.id),
    )

    if not past_contracts:
        return True

    failed = [c for c in past_contracts if c.get("status") == "FAILED"]
    completed = [c for c in past_contracts if c.get("status") in ("COMPLETED", "FAILED")]

    if len(failed) >= MAX_FAILED_CONTRACTS:
        raise ValueError(
            f"Vessel {vessel.id} has {len(failed)} failed contracts "
            f"(max {MAX_FAILED_CONTRACTS}). Ineligible for DR participation."
        )

    if len(completed) >= 3:
        fulfillment_rate = 1 - (len(failed) / len(completed))
        if fulfillment_rate < MIN_FULFILLMENT_RATE:
            raise ValueError(
                f"Vessel {vessel.id} fulfillment rate is {fulfillment_rate:.0%}, "
                f"below the required {MIN_FULFILLMENT_RATE:.0%}."
            )

    return True


def post_event_contract_validation(contract: contract.Contract):
    vessel_measurements = _measurements_client.query_gsi(
        index_name="vesselId-index",
        key_condition_expression=Key("vesselId").eq(contract.vesselId),
    )

    def _matches_contract_event(measurement):
        measurement_event_id = measurement.get("drEventId")
        if measurement_event_id is None:
            measurement_event_id = measurement.get("dreventId")

        if measurement_event_id is not None:
            return str(measurement_event_id) == str(contract.drEventId)

        measurement_contract_id = measurement.get("contractId")
        if measurement_contract_id is not None:
            return str(measurement_contract_id) == str(contract.id)

        return True

    user_measurements = [
        measurement
        for measurement in vessel_measurements
        if _matches_contract_event(measurement)
    ]

    if not user_measurements:
        raise ValueError(
            f"No measurements found for vessel={contract.vesselId} "
            f"event={contract.drEventId}. Cannot settle contract."
        )

    promised_kwh = Decimal(str(contract.energyAmount))
    delivered_kwh = sum(
        (Decimal(str(m.get("energyKwh", 0))) for m in user_measurements),
        Decimal("0"),
    )

    floor = promised_kwh * Decimal(str(1 - KW_TOLERANCE))
    status = "COMPLETED" if delivered_kwh >= floor else "FAILED"

    _contracts_client.update_item(
        key={"id": contract.id},
        update_data={"status": status}
    )

    return status

import config
from decimal import Decimal
from typing import Iterable, Optional, Union

from models.vessel import Vessel
from db.dynamoClient import DynamoClient
from models import contract
from boto3.dynamodb.conditions import Key


MAX_FAILED_CONTRACTS = 3
MIN_FULFILLMENT_RATE = 0.75
KW_TOLERANCE = 0.10


_contracts_client = DynamoClient(
    table_name=config.CONTRACTS_TABLE,
    region_name=config.AWS_REGION,
)
_measurements_client = DynamoClient(
    table_name=config.MEASUREMENTS_TABLE,
    region_name=config.AWS_REGION,
)


def _evaluate_pre_event_rules(vessel: Vessel, past_contracts: Iterable[dict]) -> bool:
    past_contracts = list(past_contracts)

    if not past_contracts:
        return True

    failed = [
        contract_data
        for contract_data in past_contracts
        if str(contract_data.get("status") or "").lower()
        == contract.ContractStatus.FAILED.value
    ]
    completed = [
        contract_data
        for contract_data in past_contracts
        if str(contract_data.get("status") or "").lower()
        in {
            contract.ContractStatus.COMPLETED.value,
            contract.ContractStatus.FAILED.value,
        }
    ]

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


def pre_event_contract_validation(
    vessel: Vessel,
    past_contracts: Optional[Iterable[dict]] = None,
) -> bool:

    if past_contracts is None:
        past_contracts = _contracts_client.query_gsi(
            index_name="vesselId-index",
            key_condition_expression=Key("vesselId").eq(vessel.id),
        )
    else:
        past_contracts = [
            contract_data
            for contract_data in past_contracts
            if str(contract_data.get("vesselId") or "") == str(vessel.id)
        ]

    return _evaluate_pre_event_rules(vessel, past_contracts)


def _coerce_contract(
    contract_data: Union[contract.Contract, dict]
) -> contract.Contract:
    if isinstance(contract_data, contract.Contract):
        return contract_data
    if isinstance(contract_data, dict):
        return contract.Contract.from_dict(dict(contract_data))
    raise TypeError("contract must be a Contract instance or a contract dictionary")


def post_event_contract_validation(
    contract_data: Union[contract.Contract, dict]
):
    validated_contract = _coerce_contract(contract_data)
    vessel_measurements = _measurements_client.query_gsi(
        index_name="vesselId-index",
        key_condition_expression=Key("vesselId").eq(validated_contract.vesselId),
    )

    def _matches_contract_event(measurement):
        for event_key in ("drEventId", "dreventId"):
            measurement_event_id = measurement.get(event_key)
            if measurement_event_id is not None:
                return str(measurement_event_id) == str(validated_contract.drEventId)

        measurement_contract_id = measurement.get("contractId")
        if measurement_contract_id is not None:
            return str(measurement_contract_id) == str(validated_contract.id)

        return True

    user_measurements = [
        measurement
        for measurement in vessel_measurements
        if _matches_contract_event(measurement)
    ]

    if not user_measurements:
        raise ValueError(
            f"No measurements found for vessel={validated_contract.vesselId} "
            f"event={validated_contract.drEventId}. Cannot settle contract."
        )

    promised_kwh = Decimal(str(validated_contract.energyAmount))
    delivered_kwh = sum(
        (Decimal(str(m.get("energyKwh", 0))) for m in user_measurements),
        Decimal("0"),
    )

    floor = promised_kwh * Decimal(str(1 - KW_TOLERANCE))
    status = (
        contract.ContractStatus.COMPLETED.value
        if delivered_kwh >= floor
        else contract.ContractStatus.FAILED.value
    )

    _contracts_client.update_item(
        key={"id": validated_contract.id},
        update_data={"status": status}
    )

    return status

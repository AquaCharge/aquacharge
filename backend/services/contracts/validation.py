
from backend.api import contracts
from backend.models.vessel import Vessel
from backend.db.dynamoClient import DynamoClient
from backend.models import contract, drevent
from boto3.dynamodb.conditions import Key


_contracts_client = DynamoClient(table_name="aquacharge-contracts-dev", region_name="us-east-1")
_measurements_client = DynamoClient(table_name="aquacharge-measurements-dev", region_name="us-east-1")

def pre_event_contract_validation(vessel: Vessel) -> bool:
    user_past_contracts = _contracts_client.query_gsi(
        index_name="vesselId-index",
        key_condition_expression=Key("vesselId").eq(vessel.id),
    )   

    num_failed_contracts = 0
    for contract in user_past_contracts:
        if contract.get("status") == "FAILED":
            num_failed_contracts += 1

    if num_failed_contracts >= 3:
        raise Exception("Vessel has 3 or more failed contracts, ineligible for DR event participation")
    else:
        return 1
    

def post_event_contract_validation(contract: contract.Contract):
    user_measurements = _measurements_client.query_gsi(
        index_name="vesselId-index",
        key_condition_expression=Key("vesselId").eq(contract.vesselId) and Key("dreventId").eq(contract.drEventId),
    )  

    if not user_measurements:
        raise Exception("No contract or measurements found for vessel and DR event")
    
    user_promise = contract[0].get("energyAmount")
    total_energy_delivered = sum([m.get("energyKwh", 0) for m in user_measurements])

    contracts.update_contract_status(contract[0].get("id"), "COMPLETED" if total_energy_delivered >= user_promise else "FAILED")
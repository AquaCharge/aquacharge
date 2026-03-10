from datetime import datetime

from models.contract import ContractStatus
from services.contracts.service import (
    ContractRepository,
    ContractService,
    ContractServiceError,
)


class InMemoryContractRepository(ContractRepository):
    def __init__(self, contracts=None):
        self.contracts = contracts or []

    def list_contracts(self):
        return self.contracts

    def get_contract(self, contract_id):
        for contract in self.contracts:
            if contract.get("id") == contract_id:
                return contract
        return None

    def create_contract(self, contract_data):
        self.contracts.append(contract_data)

    def update_contract(self, contract_id, update_data):
        contract = self.get_contract(contract_id)
        contract.update(update_data)
        return contract

    def delete_contract(self, contract_id):
        self.contracts = [c for c in self.contracts if c.get("id") != contract_id]


def _contract_payload(**overrides):
    payload = {
        "vesselId": "vessel-1",
        "drEventId": "event-1",
        "vesselName": "Test Vessel",
        "energyAmount": 10.0,
        "pricePerKwh": 2.5,
        "startTime": "2026-03-05T10:00:00",
        "endTime": "2026-03-05T12:00:00",
        "terms": "Standard dispatch terms",
        "createdBy": "admin-1",
    }
    payload.update(overrides)
    return payload


def test_create_contract_computes_total_and_normalizes_booking_id():
    repository = InMemoryContractRepository()
    service = ContractService(repository=repository)

    result = service.create_contract(_contract_payload(bookingId="  "))

    assert result["bookingId"] is None
    assert float(result["totalValue"]) == 25.0
    assert result["status"] == ContractStatus.PENDING.value


def test_update_contract_rejects_invalid_status():
    repository = InMemoryContractRepository(
        contracts=[
            {
                "id": "contract-1",
                "bookingId": None,
                "vesselId": "vessel-1",
                "drEventId": "event-1",
                "vesselName": "Test Vessel",
                "energyAmount": 10.0,
                "pricePerKwh": 2.5,
                "totalValue": 25.0,
                "startTime": "2026-03-05T10:00:00",
                "endTime": "2026-03-05T12:00:00",
                "status": ContractStatus.PENDING.value,
                "terms": "Terms",
                "createdAt": datetime.now().isoformat(),
                "createdBy": "admin-1",
            }
        ]
    )
    service = ContractService(repository=repository)

    try:
        service.update_contract("contract-1", {"status": "bad-status"})
        assert False, "Expected status validation error"
    except ContractServiceError as error:
        assert error.status_code == 400
        assert error.message == "Invalid status"


def test_cancel_contract_requires_pending_status():
    repository = InMemoryContractRepository(
        contracts=[
            {
                "id": "contract-1",
                "bookingId": None,
                "vesselId": "vessel-1",
                "drEventId": "event-1",
                "vesselName": "Test Vessel",
                "energyAmount": 10.0,
                "pricePerKwh": 2.5,
                "totalValue": 25.0,
                "startTime": "2026-03-05T10:00:00",
                "endTime": "2026-03-05T12:00:00",
                "status": ContractStatus.ACTIVE.value,
                "terms": "Terms",
                "createdAt": datetime.now().isoformat(),
                "createdBy": "admin-1",
            }
        ]
    )
    service = ContractService(repository=repository)

    try:
        service.cancel_contract("contract-1")
        assert False, "Expected cancellation rule error"
    except ContractServiceError as error:
        assert error.status_code == 400
        assert error.message == "Only pending contracts can be cancelled"


def test_complete_contract_allows_active_status():
    repository = InMemoryContractRepository(
        contracts=[
            {
                "id": "contract-1",
                "bookingId": None,
                "vesselId": "vessel-1",
                "drEventId": "event-1",
                "vesselName": "Test Vessel",
                "energyAmount": 10.0,
                "pricePerKwh": 2.5,
                "totalValue": 25.0,
                "startTime": "2026-03-05T10:00:00",
                "endTime": "2026-03-05T12:00:00",
                "status": ContractStatus.ACTIVE.value,
                "terms": "Terms",
                "createdAt": datetime.now().isoformat(),
                "createdBy": "admin-1",
            }
        ]
    )
    service = ContractService(repository=repository)

    result = service.complete_contract("contract-1")

    assert result["status"] == ContractStatus.COMPLETED.value

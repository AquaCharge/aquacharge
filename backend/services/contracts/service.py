from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from db.dynamoClient import DynamoClient
from models.contract import Contract, ContractStatus


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


class ContractServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def parse_datetime_safe(dt_string: str) -> datetime:
    return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))


class ContractRepository(Protocol):
    def list_contracts(self) -> List[Dict[str, Any]]:
        pass

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        pass

    def create_contract(self, contract_data: Dict[str, Any]) -> None:
        pass

    def update_contract(self, contract_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def delete_contract(self, contract_id: str) -> None:
        pass


class DynamoContractRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-contracts-dev", region_name="us-east-1"
        )

    def list_contracts(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        contract = self.client.get_item(key={"id": contract_id})
        return contract or None

    def create_contract(self, contract_data: Dict[str, Any]) -> None:
        self.client.put_item(item=contract_data)

    def update_contract(self, contract_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.update_item(key={"id": contract_id}, update_data=update_data)

    def delete_contract(self, contract_id: str) -> None:
        self.client.delete_item(key={"id": contract_id})


@dataclass
class ContractService:
    repository: ContractRepository

    def __init__(self, repository: Optional[ContractRepository] = None):
        self.repository = repository or DynamoContractRepository()

    def list_contracts(
        self,
        status_filter: Optional[str] = None,
        vessel_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        filtered_contracts: List[Dict[str, Any]] = []
        for contract_data in self.repository.list_contracts():
            if status_filter and contract_data.get("status") != status_filter:
                continue
            if vessel_id and contract_data.get("vesselId") != vessel_id:
                continue

            contract = Contract.from_dict(contract_data)
            filtered_contracts.append(contract.to_public_dict())

        filtered_contracts.sort(key=lambda item: item["createdAt"], reverse=True)
        return filtered_contracts

    def get_contract(self, contract_id: str) -> Dict[str, Any]:
        contract_data = self.repository.get_contract(contract_id)
        if not contract_data:
            raise ContractServiceError("Contract not found", 404)
        contract = Contract.from_dict(contract_data)
        return contract.to_public_dict()

    def create_contract(self, data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = [
            "vesselId",
            "drEventId",
            "vesselName",
            "energyAmount",
            "pricePerKwh",
            "startTime",
            "endTime",
            "terms",
        ]
        for field in required_fields:
            if field not in data:
                raise ContractServiceError(f"{field} is required", 400)

        try:
            start_time = parse_datetime_safe(data["startTime"])
            end_time = parse_datetime_safe(data["endTime"])
        except ValueError as error:
            raise ContractServiceError(
                "Invalid date format. Use ISO format.", 400
            ) from error

        booking_id = data.get("bookingId")
        if isinstance(booking_id, str):
            booking_id = booking_id.strip() or None

        contract = Contract(
            bookingId=booking_id,
            vesselId=data["vesselId"],
            drEventId=data["drEventId"],
            vesselName=data["vesselName"],
            energyAmount=Decimal(str(data["energyAmount"])),
            pricePerKwh=Decimal(str(data["pricePerKwh"])),
            startTime=start_time,
            endTime=end_time,
            terms=data["terms"],
            createdBy=data.get("createdBy", "unknown"),
        )
        contract.totalValue = contract.energyAmount * contract.pricePerKwh

        try:
            contract.validate()
        except ValueError as error:
            raise ContractServiceError(str(error), 400) from error

        contract_data = contract.to_dict()
        contract_data = {key: value for key, value in contract_data.items() if value is not None}
        self.repository.create_contract(contract_data)
        return contract.to_public_dict()

    def update_contract(self, contract_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        contract = Contract.from_dict(existing_data)

        if "status" in data:
            allowed_statuses = [status.value for status in ContractStatus]
            if data["status"] not in allowed_statuses:
                raise ContractServiceError("Invalid status", 400)
            contract.status = data["status"]

        if "terms" in data:
            contract.terms = data["terms"]

        contract.updatedAt = datetime.now()
        self.repository.update_contract(
            contract_id,
            {
                "status": contract.status,
                "terms": contract.terms,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )

        return contract.to_public_dict()

    def cancel_contract(self, contract_id: str) -> Dict[str, Any]:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        contract = Contract.from_dict(existing_data)
        if contract.status != ContractStatus.PENDING.value:
            raise ContractServiceError("Only pending contracts can be cancelled", 400)

        contract.status = ContractStatus.CANCELLED.value
        contract.updatedAt = datetime.now()
        self.repository.update_contract(
            contract_id,
            {
                "status": contract.status,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )

        return contract.to_public_dict()

    def complete_contract(self, contract_id: str) -> Dict[str, Any]:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        contract = Contract.from_dict(existing_data)
        if contract.status not in [
            ContractStatus.PENDING.value,
            ContractStatus.ACTIVE.value,
        ]:
            raise ContractServiceError(
                "Only pending or active contracts can be completed",
                400,
            )

        contract.status = ContractStatus.COMPLETED.value
        contract.updatedAt = datetime.now()
        self.repository.update_contract(
            contract_id,
            {
                "status": contract.status,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )

        return contract.to_public_dict()

    def delete_contract(self, contract_id: str) -> None:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        self.repository.delete_contract(contract_id)

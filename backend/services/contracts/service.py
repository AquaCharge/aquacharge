from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol
import uuid

from db.dynamoClient import DynamoClient
from models.booking import Booking, BookingStatus
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

    def update_contract(
        self, contract_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    def delete_contract(self, contract_id: str) -> None:
        pass


class BookingRepository(Protocol):
    def list_bookings(self) -> List[Dict[str, Any]]:
        pass

    def create_booking(self, booking_data: Dict[str, Any]) -> None:
        pass


class VesselRepository(Protocol):
    def get_vessel(self, vessel_id: str) -> Optional[Dict[str, Any]]:
        pass


class DREventRepository(Protocol):
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
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

    def update_contract(
        self, contract_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.client.update_item(key={"id": contract_id}, update_data=update_data)

    def delete_contract(self, contract_id: str) -> None:
        self.client.delete_item(key={"id": contract_id})


class DynamoBookingRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-bookings-dev", region_name="us-east-1"
        )

    def list_bookings(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def create_booking(self, booking_data: Dict[str, Any]) -> None:
        self.client.put_item(item=booking_data)


class DynamoVesselRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-vessels-dev", region_name="us-east-1"
        )

    def get_vessel(self, vessel_id: str) -> Optional[Dict[str, Any]]:
        vessel = self.client.get_item(key={"id": vessel_id})
        return vessel or None


class DynamoDREventRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-drevents-dev", region_name="us-east-1"
        )

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        event = self.client.get_item(key={"id": event_id})
        return event or None


@dataclass
class ContractService:
    repository: ContractRepository

    def __init__(
        self,
        repository: Optional[ContractRepository] = None,
        booking_repository: Optional[BookingRepository] = None,
        vessel_repository: Optional[VesselRepository] = None,
        drevent_repository: Optional[DREventRepository] = None,
    ):
        self.repository = repository or DynamoContractRepository()
        self.booking_repository = booking_repository or DynamoBookingRepository()
        self.vessel_repository = vessel_repository or DynamoVesselRepository()
        self.drevent_repository = drevent_repository or DynamoDREventRepository()

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
        contract_data = {
            key: value for key, value in contract_data.items() if value is not None
        }
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

    # ------------------------------------------------------------------
    # Dispatch: generate contracts for all eligible vessels
    # ------------------------------------------------------------------

    def dispatch_event(
        self,
        dr_event: Dict[str, Any],
        eligible_vessels: List[Dict[str, Any]],
        caller_user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate one pending contract per eligible vessel (up to maxParticipants).

        Parameters
        ----------
        dr_event:
            Serialised DR event dict (as returned by DREventService.get_event).
        eligible_vessels:
            List of vessel result dicts from EligibilityService (eligible==True only).
        caller_user_id:
            ID of the PSO user triggering dispatch (stored as createdBy).

        Returns
        -------
        List of created contract public dicts.
        """
        max_participants = int(dr_event.get("maxParticipants") or 0)
        target_energy_kwh = float(dr_event.get("targetEnergyKwh") or 0)
        price_per_kwh = float(dr_event.get("pricePerKwh") or 0)
        start_time = dr_event.get("startTime", "")
        end_time = dr_event.get("endTime", "")
        event_id = dr_event.get("id", "")

        slots = (
            eligible_vessels[:max_participants]
            if max_participants > 0
            else eligible_vessels
        )
        n = len(slots)
        if n == 0:
            return []

        energy_per_vessel = round(target_energy_kwh / n, 6) if n > 0 else 0.0

        created: List[Dict[str, Any]] = []
        for vessel_result in slots:
            vessel_id = vessel_result.get("vesselId", "")
            display_name = vessel_result.get("displayName") or vessel_id

            contract_data = {
                "vesselId": vessel_id,
                "drEventId": event_id,
                "vesselName": display_name,
                "energyAmount": energy_per_vessel,
                "pricePerKwh": price_per_kwh,
                "startTime": start_time,
                "endTime": end_time,
                "terms": (
                    f"DR event contract for event {event_id}. "
                    f"Vessel must deliver {energy_per_vessel:.2f} kWh at "
                    f"${price_per_kwh}/kWh between {start_time} and {end_time}."
                ),
                "createdBy": caller_user_id,
            }
            contract = self.create_contract(contract_data)
            created.append(contract)

        return created

    # ------------------------------------------------------------------
    # Accept: ownership check → schedule conflict check → dock reservation
    # ------------------------------------------------------------------

    def accept_contract(
        self, contract_id: str, caller_vessel_ids: List[str]
    ) -> Dict[str, Any]:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        contract = Contract.from_dict(existing_data)

        # --- ownership guard ---
        if contract.vesselId not in caller_vessel_ids:
            raise ContractServiceError(
                "You do not own the vessel on this contract", 403
            )

        # --- status guard ---
        if contract.status != ContractStatus.PENDING.value:
            raise ContractServiceError("Only pending contracts can be accepted", 400)

        # --- resolve window ---
        try:
            contract_start = parse_datetime_safe(
                contract.startTime.isoformat()
                if isinstance(contract.startTime, datetime)
                else str(contract.startTime)
            )
            contract_end = parse_datetime_safe(
                contract.endTime.isoformat()
                if isinstance(contract.endTime, datetime)
                else str(contract.endTime)
            )
        except (ValueError, AttributeError) as error:
            raise ContractServiceError(
                "Contract has invalid time window", 400
            ) from error

        # --- schedule conflict check (vessel-level) ---
        for existing_booking in self.booking_repository.list_bookings():
            if existing_booking.get("vesselId") != contract.vesselId:
                continue
            if existing_booking.get("status") not in [
                BookingStatus.PENDING.value,
                BookingStatus.CONFIRMED.value,
            ]:
                continue
            try:
                b_start = parse_datetime_safe(str(existing_booking["startTime"]))
                b_end = parse_datetime_safe(str(existing_booking["endTime"]))
            except (KeyError, ValueError):
                continue
            if not (contract_end <= b_start or contract_start >= b_end):
                raise ContractServiceError(
                    "Vessel already has a booking that conflicts with this contract window",
                    409,
                )

        # --- dock reservation ---
        # Look up the DR event to get stationId and chargerType context.
        dr_event_data = self.drevent_repository.get_event(contract.drEventId)
        if not dr_event_data:
            raise ContractServiceError("Associated DR event not found", 404)

        station_id = dr_event_data.get("stationId", "")

        # Use the vessel's chargerType for the booking.
        vessel_data = self.vessel_repository.get_vessel(contract.vesselId)
        charger_type = (vessel_data or {}).get("chargerType", "AC")

        # Determine the vessel's owning userId for the booking record.
        vessel_user_id = (vessel_data or {}).get("userId", "system")

        # Check station-level dock conflict (same station, overlapping Pending/Confirmed booking).
        for existing_booking in self.booking_repository.list_bookings():
            if existing_booking.get("stationId") != station_id:
                continue
            if existing_booking.get("status") not in [
                BookingStatus.PENDING.value,
                BookingStatus.CONFIRMED.value,
            ]:
                continue
            try:
                b_start = parse_datetime_safe(str(existing_booking["startTime"]))
                b_end = parse_datetime_safe(str(existing_booking["endTime"]))
            except (KeyError, ValueError):
                continue
            if not (contract_end <= b_start or contract_start >= b_end):
                raise ContractServiceError(
                    "Dock at event station is already reserved for this time window",
                    409,
                )

        # Create the dock booking.
        booking = Booking(
            id=str(uuid.uuid4()),
            userId=vessel_user_id,
            vesselId=contract.vesselId,
            stationId=station_id,
            startTime=contract_start,
            endTime=contract_end,
            chargerType=charger_type,
            status=BookingStatus.PENDING,
            createdAt=datetime.now(timezone.utc),
        )
        booking_dict = {
            "id": booking.id,
            "userId": booking.userId,
            "vesselId": booking.vesselId,
            "stationId": booking.stationId,
            "startTime": booking.startTime.isoformat(),
            "endTime": booking.endTime.isoformat(),
            "chargerType": booking.chargerType,
            "status": BookingStatus.PENDING.value,
            "createdAt": (
                booking.createdAt.isoformat()
                if isinstance(booking.createdAt, datetime)
                else str(booking.createdAt)
            ),
        }
        self.booking_repository.create_booking(booking_dict)

        # --- transition contract to active, store bookingId ---
        contract.status = ContractStatus.ACTIVE.value
        contract.bookingId = booking.id
        contract.updatedAt = datetime.now()
        self.repository.update_contract(
            contract_id,
            {
                "status": contract.status,
                "bookingId": contract.bookingId,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )
        return contract.to_public_dict()

    def decline_contract(
        self, contract_id: str, caller_vessel_ids: List[str]
    ) -> Dict[str, Any]:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        contract = Contract.from_dict(existing_data)
        if contract.vesselId not in caller_vessel_ids:
            raise ContractServiceError(
                "You do not own the vessel on this contract", 403
            )
        if contract.status != ContractStatus.PENDING.value:
            raise ContractServiceError("Only pending contracts can be declined", 400)

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

    def delete_contract(self, contract_id: str) -> None:
        existing_data = self.repository.get_contract(contract_id)
        if not existing_data:
            raise ContractServiceError("Contract not found", 404)

        self.repository.delete_contract(contract_id)

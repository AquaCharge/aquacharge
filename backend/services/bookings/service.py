from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol

import config
from db.dynamoClient import DynamoClient
from models.booking import Booking, BookingStatus
from models.contract import ContractStatus
from services.drevents import DREventService, DREventServiceError


class BookingServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def parse_datetime_safe(dt_string: str) -> datetime:
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_active_booking_status(status: Any) -> bool:
    return status in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]


def _booking_windows_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    return not (end_a <= start_b or start_a >= end_b)


def _is_active_charger(charger: Dict[str, Any]) -> bool:
    status = charger.get("status")
    return status in [1, "ACTIVE", "active", "Active", "1"]


class BookingRepository(Protocol):
    def list_bookings(self) -> List[Dict[str, Any]]:
        pass

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        pass

    def create_booking(self, booking: Dict[str, Any]) -> None:
        pass

    def update_booking(
        self, booking_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    def delete_booking(self, booking_id: str) -> None:
        pass


class ChargerRepository(Protocol):
    def get_charger(self, charger_id: str) -> Optional[Dict[str, Any]]:
        pass

    def list_station_chargers(self, station_id: str) -> List[Dict[str, Any]]:
        pass


class ContractRepository(Protocol):
    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        pass

    def list_contracts(self) -> List[Dict[str, Any]]:
        pass

    def update_contract(
        self, contract_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass


class DREventLifecycleService(Protocol):
    def get_event(self, event_id: str) -> Dict[str, Any]:
        pass

    def update_event(self, event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass


class DynamoBookingRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.BOOKINGS_TABLE, region_name=config.AWS_REGION
        )

    def list_bookings(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        booking = self.client.get_item(key={"id": booking_id})
        return booking or None

    def create_booking(self, booking: Dict[str, Any]) -> None:
        self.client.put_item(booking)

    def update_booking(
        self, booking_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.client.update_item(key={"id": booking_id}, update_data=update_data)

    def delete_booking(self, booking_id: str) -> None:
        self.client.delete_item(key={"id": booking_id})


class DynamoChargerRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.CHARGERS_TABLE, region_name=config.AWS_REGION
        )

    def get_charger(self, charger_id: str) -> Optional[Dict[str, Any]]:
        charger = self.client.get_item(key={"id": charger_id})
        return charger or None

    def list_station_chargers(self, station_id: str) -> List[Dict[str, Any]]:
        return [
            charger
            for charger in self.client.scan_items()
            if str(charger.get("chargingStationId") or "") == station_id
        ]


class DynamoContractRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.CONTRACTS_TABLE, region_name=config.AWS_REGION
        )

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        contract = self.client.get_item(key={"id": contract_id})
        return contract or None

    def list_contracts(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def update_contract(
        self, contract_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.client.update_item(key={"id": contract_id}, update_data=update_data)


@dataclass
class BookingService:
    repository: BookingRepository
    charger_repository: ChargerRepository
    contract_repository: ContractRepository
    drevent_service: DREventLifecycleService
    now_provider: Callable[[], datetime]

    def __init__(
        self,
        repository: Optional[BookingRepository] = None,
        charger_repository: Optional[ChargerRepository] = None,
        contract_repository: Optional[ContractRepository] = None,
        drevent_service: Optional[DREventLifecycleService] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
    ):
        self.repository = repository or DynamoBookingRepository()
        self.charger_repository = charger_repository or DynamoChargerRepository()
        self.contract_repository = contract_repository or DynamoContractRepository()
        self.drevent_service = drevent_service or DREventService()
        self.now_provider = now_provider or now_utc

    def list_bookings(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        bookings = self.repository.list_bookings()

        if user_id:
            bookings = [
                booking for booking in bookings if booking.get("userId") == user_id
            ]

        if status:
            try:
                status_enum = BookingStatus[status.upper()]
            except KeyError as error:
                raise BookingServiceError("Invalid status", 400) from error
            bookings = [
                booking
                for booking in bookings
                if booking.get("status") == status_enum.value
            ]

        return bookings

    def get_booking(self, booking_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)
        self._assert_booking_ownership(booking, user_id)
        return booking

    def create_booking(self, data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = [
            "userId",
            "vesselId",
            "stationId",
            "startTime",
            "endTime",
        ]
        for field in required_fields:
            if field not in data:
                raise BookingServiceError(f"{field} is required", 400)

        try:
            start_time = parse_datetime_safe(data["startTime"])
            end_time = parse_datetime_safe(data["endTime"])
        except ValueError as error:
            raise BookingServiceError(
                "Invalid datetime format. Use ISO format.", 400
            ) from error

        if end_time <= start_time:
            raise BookingServiceError("End time must be after start time", 400)

        station_id = str(data["stationId"])
        charger_id = str(data.get("chargerId") or "").strip()
        if not charger_id:
            charger_id = self._resolve_charger_id(
                station_id=station_id,
                charger_type=str(data.get("chargerType") or "").strip(),
                start_time=start_time,
                end_time=end_time,
            )
            if not charger_id:
                raise BookingServiceError("chargerId is required", 400)
            data["chargerId"] = charger_id

        charger = self.charger_repository.get_charger(charger_id)
        if not charger:
            raise BookingServiceError("Charger not found", 404)

        charger_station_id = str(charger.get("chargingStationId") or "")
        if charger_station_id != station_id:
            raise BookingServiceError("Charger does not belong to the requested station", 400)

        if not _is_active_charger(charger):
            raise BookingServiceError("Selected charger is unavailable", 409)

        contract = None
        contract_id = str(data.get("contractId") or "").strip()
        if contract_id:
            contract = self.contract_repository.get_contract(contract_id)
            if not contract:
                raise BookingServiceError("Contract not found", 404)
            if str(contract.get("vesselId") or "") != str(data["vesselId"]):
                raise BookingServiceError("Contract does not belong to this vessel", 403)
            if str(contract.get("bookingId") or "").strip():
                raise BookingServiceError("Contract already has a booking", 409)

        self._assert_no_charger_conflict(
            charger_id=str(data["chargerId"]),
            start_time=start_time,
            end_time=end_time,
        )

        try:
            status = BookingStatus[data.get("status", "CONFIRMED").upper()]
        except KeyError as error:
            raise BookingServiceError("Invalid status", 400) from error

        booking = Booking(
            userId=str(data["userId"]),
            vesselId=str(data["vesselId"]),
            stationId=station_id,
            chargerId=charger_id,
            startTime=start_time,
            endTime=end_time,
            chargerType=str(charger.get("chargerType") or ""),
            status=status,
        )

        booking_data = booking.to_dict()
        self.repository.create_booking(booking_data)

        if contract_id:
            self.contract_repository.update_contract(
                contract_id,
                {
                    "bookingId": booking.id,
                    "status": ContractStatus.ACTIVE.value,
                    "updatedAt": self.now_provider().isoformat(),
                },
            )
            self._transition_event_to_committed_if_ready(str(contract.get("drEventId") or ""))

        return booking_data

    def update_booking(
        self,
        booking_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)
        self._assert_booking_ownership(booking, user_id)

        if "status" in data:
            try:
                status_enum = BookingStatus[data["status"].upper()]
            except KeyError as error:
                raise BookingServiceError("Invalid status", 400) from error
            else:
                update_data: Dict[str, Any] = {"status": status_enum.value}
        else:
            update_data = {}

        start_time = parse_datetime_safe(str(booking["startTime"]))
        if start_time - self.now_provider() <= timedelta(hours=4):
            raise BookingServiceError(
                "Bookings cannot be modified within 4 hours of start time",
                400,
            )

        next_start_time = start_time
        next_end_time = parse_datetime_safe(str(booking["endTime"]))
        next_charger_id = str(booking.get("chargerId") or "")
        next_station_id = str(booking.get("stationId") or "")

        try:
            if "startTime" in data:
                next_start_time = parse_datetime_safe(data["startTime"])
                update_data["startTime"] = next_start_time.isoformat()
            if "endTime" in data:
                next_end_time = parse_datetime_safe(data["endTime"])
                update_data["endTime"] = next_end_time.isoformat()
        except ValueError as error:
            raise BookingServiceError(
                "Invalid datetime format. Use ISO format.", 400
            ) from error

        if next_end_time <= next_start_time:
            raise BookingServiceError("End time must be after start time", 400)

        if "chargerId" in data:
            charger = self.charger_repository.get_charger(str(data["chargerId"]))
            if not charger:
                raise BookingServiceError("Charger not found", 404)
            if not _is_active_charger(charger):
                raise BookingServiceError("Selected charger is unavailable", 409)
            charger_station_id = str(charger.get("chargingStationId") or "")
            if charger_station_id != next_station_id:
                raise BookingServiceError("Charger does not belong to the requested station", 400)
            next_charger_id = str(data["chargerId"])
            update_data["chargerId"] = next_charger_id
            update_data["chargerType"] = str(charger.get("chargerType") or "")

        self._assert_no_charger_conflict(
            charger_id=next_charger_id,
            start_time=next_start_time,
            end_time=next_end_time,
            excluded_booking_id=booking_id,
        )

        return self.repository.update_booking(booking_id, update_data)

    def cancel_booking(
        self,
        booking_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        booking = self.repository.get_booking(booking_id)
        if not booking:
            raise BookingServiceError("Booking not found", 404)
        self._assert_booking_ownership(booking, user_id)

        if booking.get("status") == BookingStatus.COMPLETED.value:
            raise BookingServiceError("Cannot cancel completed booking", 400)

        if self._linked_contract(booking_id) is not None:
            start_time = parse_datetime_safe(str(booking["startTime"]))
            if start_time - self.now_provider() <= timedelta(hours=4):
                raise BookingServiceError(
                    "Contract-linked bookings cannot be cancelled within 4 hours of start time",
                    400,
                )

        return self.repository.update_booking(
            booking_id,
            {"status": BookingStatus.CANCELLED.value},
        )

    def delete_booking(
        self,
        booking_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.cancel_booking(booking_id, user_id=user_id)

    def list_upcoming_bookings(self, user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            raise BookingServiceError("userId parameter is required", 400)

        upcoming: List[Dict[str, Any]] = []
        current_time = self.now_provider()
        for booking in self.repository.list_bookings():
            start_time = parse_datetime_safe(str(booking["startTime"]))
            if (
                booking.get("userId") == user_id
                and start_time > current_time
                and _is_active_booking_status(booking.get("status"))
            ):
                upcoming.append(booking)

        upcoming.sort(key=lambda booking: booking["startTime"])
        return upcoming

    def get_station_availability(
        self,
        station_id: str,
        start_time_raw: str,
        end_time_raw: str,
    ) -> Dict[str, Any]:
        try:
            start_time = parse_datetime_safe(start_time_raw)
            end_time = parse_datetime_safe(end_time_raw)
        except ValueError as error:
            raise BookingServiceError(
                "Invalid datetime format. Use ISO format.", 400
            ) from error

        if end_time <= start_time:
            raise BookingServiceError("End time must be after start time", 400)

        chargers = self.charger_repository.list_station_chargers(station_id)
        availability = []
        for charger in chargers:
            charger_id = str(charger.get("id") or "")
            has_conflict = self._charger_has_conflict(
                charger_id=charger_id,
                start_time=start_time,
                end_time=end_time,
            )
            availability.append(
                {
                    "chargerId": charger_id,
                    "chargerType": charger.get("chargerType"),
                    "maxRate": charger.get("maxRate"),
                    "status": charger.get("status"),
                    "available": _is_active_charger(charger) and not has_conflict,
                }
            )

        return {
            "stationId": station_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "chargers": availability,
        }

    def _assert_booking_ownership(
        self,
        booking: Dict[str, Any],
        user_id: Optional[str],
    ) -> None:
        if user_id and booking.get("userId") != user_id:
            raise BookingServiceError("You do not own this booking", 403)

    def _assert_no_charger_conflict(
        self,
        charger_id: str,
        start_time: datetime,
        end_time: datetime,
        excluded_booking_id: Optional[str] = None,
    ) -> None:
        if self._charger_has_conflict(
            charger_id=charger_id,
            start_time=start_time,
            end_time=end_time,
            excluded_booking_id=excluded_booking_id,
        ):
            raise BookingServiceError("Time slot conflicts with existing booking", 409)

    def _charger_has_conflict(
        self,
        charger_id: str,
        start_time: datetime,
        end_time: datetime,
        excluded_booking_id: Optional[str] = None,
    ) -> bool:
        for existing_booking in self.repository.list_bookings():
            if excluded_booking_id and existing_booking.get("id") == excluded_booking_id:
                continue
            if str(existing_booking.get("chargerId") or "") != charger_id:
                continue
            if not _is_active_booking_status(existing_booking.get("status")):
                continue

            existing_start = parse_datetime_safe(str(existing_booking["startTime"]))
            existing_end = parse_datetime_safe(str(existing_booking["endTime"]))
            if _booking_windows_overlap(start_time, end_time, existing_start, existing_end):
                return True
        return False

    def _linked_contract(self, booking_id: str) -> Optional[Dict[str, Any]]:
        for contract in self.contract_repository.list_contracts():
            if str(contract.get("bookingId") or "") == booking_id:
                return contract
        return None

    def _resolve_charger_id(
        self,
        station_id: str,
        charger_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> str:
        for charger in self.charger_repository.list_station_chargers(station_id):
            charger_id = str(charger.get("id") or "")
            if not charger_id:
                continue
            if charger_type and str(charger.get("chargerType") or "") != charger_type:
                continue
            if not _is_active_charger(charger):
                continue
            if self._charger_has_conflict(
                charger_id=charger_id,
                start_time=start_time,
                end_time=end_time,
            ):
                continue
            return charger_id
        return ""

    def _transition_event_to_committed_if_ready(self, dr_event_id: str) -> None:
        if not dr_event_id:
            return

        try:
            dr_event = self.drevent_service.get_event(dr_event_id)
        except DREventServiceError:
            return

        if str(dr_event.get("status") or "") != "Accepted":
            return

        has_booked_active_contract = any(
            str(contract.get("drEventId") or "") == dr_event_id
            and str(contract.get("status") or "").lower() == ContractStatus.ACTIVE.value
            and bool(str(contract.get("bookingId") or "").strip())
            for contract in self.contract_repository.list_contracts()
        )
        if not has_booked_active_contract:
            return

        self.drevent_service.update_event(
            dr_event_id,
            {"status": "Committed"},
        )

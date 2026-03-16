from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

import config
from db.dynamoClient import DynamoClient
from models.drevent import DREvent, EventStatus


def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class DREventServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DREventRepository(Protocol):
    def list_events(self) -> List[Dict[str, Any]]:
        pass

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        pass

    def put_event(self, event_data: Dict[str, Any]) -> None:
        pass

    def update_event(
        self, event_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass


class MeasurementRepository(Protocol):
    def list_measurements(self) -> List[Dict[str, Any]]:
        pass


class StationRepository(Protocol):
    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        pass


class DynamoDREventRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.DREVENTS_TABLE, region_name=config.AWS_REGION
        )

    def list_events(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        return self.client.get_item(key={"id": event_id}) or None

    def put_event(self, event_data: Dict[str, Any]) -> None:
        self.client.put_item(item=event_data)

    def update_event(
        self, event_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.client.update_item(key={"id": event_id}, update_data=update_data)


class DynamoMeasurementRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.MEASUREMENTS_TABLE, region_name=config.AWS_REGION
        )

    def list_measurements(self) -> List[Dict[str, Any]]:
        try:
            return self.client.scan_items()
        except Exception:
            return []


class DynamoStationRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.STATIONS_TABLE, region_name=config.AWS_REGION
        )

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        return self.client.get_item(key={"id": station_id}) or None


def serialize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    drevent = DREvent.from_dict(dict(event))
    return convert_decimals(drevent.to_public_dict())


ALLOWED_TRANSITIONS = {
    EventStatus.CREATED.value: {
        EventStatus.DISPATCHED.value,
        EventStatus.CANCELLED.value,
    },
    EventStatus.DISPATCHED.value: {
        EventStatus.ACCEPTED.value,
        EventStatus.CANCELLED.value,
    },
    EventStatus.ACCEPTED.value: {
        EventStatus.COMMITTED.value,
        EventStatus.CANCELLED.value,
    },
    EventStatus.COMMITTED.value: {
        EventStatus.ACTIVE.value,
        EventStatus.CANCELLED.value,
    },
    EventStatus.ACTIVE.value: {
        EventStatus.COMPLETED.value,
        EventStatus.CANCELLED.value,
    },
    EventStatus.COMPLETED.value: {EventStatus.SETTLED.value},
    EventStatus.SETTLED.value: {EventStatus.ARCHIVED.value},
    EventStatus.ARCHIVED.value: set(),
    EventStatus.CANCELLED.value: set(),
}


@dataclass
class DREventService:
    event_repository: DREventRepository
    measurement_repository: MeasurementRepository
    station_repository: StationRepository

    def __init__(
        self,
        event_repository: Optional[DREventRepository] = None,
        measurement_repository: Optional[MeasurementRepository] = None,
        station_repository: Optional[StationRepository] = None,
    ):
        self.event_repository = event_repository or DynamoDREventRepository()
        self.measurement_repository = (
            measurement_repository or DynamoMeasurementRepository()
        )
        self.station_repository = station_repository or DynamoStationRepository()

    def list_events(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        events = [serialize_event(item) for item in self.event_repository.list_events()]
        if status_filter:
            events = [event for event in events if event.get("status") == status_filter]
        events.sort(
            key=lambda item: parse_datetime(item.get("startTime"))
            or datetime.max.replace(tzinfo=timezone.utc)
        )
        return events

    def get_event(self, event_id: str) -> Dict[str, Any]:
        event = self.event_repository.get_event(event_id)
        if not event:
            raise DREventServiceError("DR event not found", 404)
        return serialize_event(event)

    def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized_data = self._sanitize_event_input(data)
        required_fields = [
            "stationId",
            "pricePerKwh",
            "targetEnergyKwh",
            "maxParticipants",
            "startTime",
            "endTime",
        ]
        for field in required_fields:
            if field not in sanitized_data:
                raise DREventServiceError(f"{field} is required", 400)

        try:
            drevent = DREvent(
                stationId=sanitized_data["stationId"],
                pricePerKwh=Decimal(str(sanitized_data["pricePerKwh"])),
                targetEnergyKwh=Decimal(str(sanitized_data["targetEnergyKwh"])),
                maxParticipants=int(sanitized_data["maxParticipants"]),
                startTime=datetime.fromisoformat(
                    sanitized_data["startTime"].replace("Z", "+00:00")
                ),
                endTime=datetime.fromisoformat(
                    sanitized_data["endTime"].replace("Z", "+00:00")
                ),
                status=EventStatus.CREATED,
                details=sanitized_data.get("details", {}),
                createdAt=datetime.now(timezone.utc).isoformat(),
            )
            drevent.validate()
        except ValueError as error:
            raise DREventServiceError(str(error), 400) from error

        event_data = drevent.to_dict()
        self.event_repository.put_event(event_data)
        return serialize_event(event_data)

    def update_event(self, event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.event_repository.get_event(event_id)
        if not existing:
            raise DREventServiceError("DR event not found", 404)

        sanitized_data = self._sanitize_event_input(data)
        drevent = DREvent.from_dict(dict(existing))

        if "status" in sanitized_data:
            next_status = sanitized_data["status"]
            self._validate_transition(drevent.status.value, next_status)
            drevent.status = EventStatus(next_status)

        if "pricePerKwh" in sanitized_data:
            drevent.pricePerKwh = Decimal(str(sanitized_data["pricePerKwh"]))
        if "targetEnergyKwh" in sanitized_data:
            drevent.targetEnergyKwh = Decimal(str(sanitized_data["targetEnergyKwh"]))
        if "maxParticipants" in sanitized_data:
            drevent.maxParticipants = int(sanitized_data["maxParticipants"])
        if "startTime" in sanitized_data:
            drevent.startTime = datetime.fromisoformat(
                sanitized_data["startTime"].replace("Z", "+00:00")
            )
        if "endTime" in sanitized_data:
            drevent.endTime = datetime.fromisoformat(
                sanitized_data["endTime"].replace("Z", "+00:00")
            )
        if "details" in sanitized_data:
            drevent.details = sanitized_data["details"]

        try:
            drevent.validate()
        except ValueError as error:
            raise DREventServiceError(str(error), 400) from error

        event_data = drevent.to_dict()
        self.event_repository.put_event(event_data)
        return serialize_event(event_data)

    def _validate_transition(self, current_status: str, next_status: str) -> None:
        if next_status not in ALLOWED_TRANSITIONS:
            raise DREventServiceError("Invalid status", 400)
        if next_status == current_status:
            return
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise DREventServiceError(
                f"Invalid status transition from {current_status} to {next_status}",
                400,
            )

    def _sanitize_event_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = dict(data)
        sanitized.pop("contractId", None)
        return sanitized

    def get_monitoring_snapshot(
        self,
        event_id: Optional[str] = None,
        region: Optional[str] = None,
        period_hours: int = 24,
    ) -> Dict[str, Any]:
        period_hours = max(1, min(period_hours, 168))
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(hours=period_hours)

        events = self.list_events()
        filtered_events = []
        normalized_region = (region or "").strip().lower()
        for event in events:
            if event_id and event.get("id") != event_id:
                continue

            station = self.station_repository.get_station(event.get("stationId"))
            if normalized_region:
                region_parts = [
                    str(station.get("city", "")).lower() if station else "",
                    str(station.get("provinceOrState", "")).lower() if station else "",
                    str(station.get("country", "")).lower() if station else "",
                ]
                if normalized_region not in " ".join(region_parts):
                    continue

            filtered_events.append(
                {
                    **event,
                    "station": station or {},
                }
            )

        selected_event = None
        if event_id:
            selected_event = next(
                (event for event in filtered_events if event["id"] == event_id), None
            )
            if selected_event is None:
                raise DREventServiceError("DR event not found", 404)
        elif filtered_events:
            selected_event = sorted(
                filtered_events,
                key=lambda item: parse_datetime(item.get("startTime"))
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )[0]

        selected_event_id = selected_event.get("id") if selected_event else None
        measurements = []
        for measurement in self.measurement_repository.list_measurements():
            measurement_time = parse_datetime(
                measurement.get("timestamp") or measurement.get("createdAt")
            )
            if measurement_time is None or measurement_time < period_start:
                continue
            if selected_event_id and measurement.get("drEventId") != selected_event_id:
                continue
            measurements.append(
                {
                    **measurement,
                    "timestamp": measurement_time,
                    "energyKwh": float(measurement.get("energyKwh", 0) or 0),
                    "powerKw": float(measurement.get("powerKw", 0) or 0),
                    "currentSOC": float(measurement.get("currentSOC", 0) or 0),
                }
            )

        vessel_latest: Dict[str, Dict[str, Any]] = {}
        energy_delivered = 0.0
        time_series: Dict[str, Dict[str, Any]] = {}
        vessel_series: Dict[str, Dict[str, Any]] = {}
        for measurement in measurements:
            energy_delivered += measurement["energyKwh"]
            vessel_id = measurement.get("vesselId")
            previous = vessel_latest.get(vessel_id)
            if previous is None or measurement["timestamp"] >= previous["timestamp"]:
                vessel_latest[vessel_id] = measurement

            bucket = (
                measurement["timestamp"].replace(second=0, microsecond=0).isoformat()
            )
            bucket_item = time_series.setdefault(
                bucket,
                {
                    "timestamp": bucket,
                    "energyDischargedKwh": 0.0,
                    "cumulativeEnergyDischargedKwh": 0.0,
                    "v2gContributionKw": 0.0,
                    "gridLoadWithoutV2GKw": None,
                    "gridLoadWithV2GKw": None,
                },
            )
            bucket_item["energyDischargedKwh"] += measurement["energyKwh"]
            bucket_item["v2gContributionKw"] += measurement["powerKw"]

            if vessel_id:
                vessel_item = vessel_series.setdefault(
                    vessel_id,
                    {
                        "vesselId": vessel_id,
                        "contractId": measurement.get("contractId"),
                        "points": {},
                    },
                )
                if measurement.get("contractId"):
                    vessel_item["contractId"] = measurement.get("contractId")
                point = vessel_item["points"].setdefault(
                    bucket,
                    {
                        "timestamp": bucket,
                        "energyDischargedKwh": 0.0,
                        "cumulativeEnergyDischargedKwh": 0.0,
                        "v2gContributionKw": 0.0,
                    },
                )
                point["energyDischargedKwh"] += measurement["energyKwh"]
                point["v2gContributionKw"] += measurement["powerKw"]

        vessel_rates = []
        for vessel_id, measurement in vessel_latest.items():
            vessel_rates.append(
                {
                    "vesselId": vessel_id,
                    "contractId": measurement.get("contractId"),
                    "dischargeRateKw": round(measurement["powerKw"], 2),
                    "currentSoc": round(measurement["currentSOC"], 2),
                    "timestamp": measurement["timestamp"].isoformat(),
                }
            )
        vessel_rates.sort(key=lambda item: item["dischargeRateKw"], reverse=True)

        vessel_curve = []
        for vessel_id, series in vessel_series.items():
            latest_measurement = vessel_latest.get(vessel_id, {})
            points = sorted(
                series["points"].values(), key=lambda item: item["timestamp"]
            )
            cumulative_energy = 0.0
            for point in points:
                cumulative_energy += point["energyDischargedKwh"]
                point["cumulativeEnergyDischargedKwh"] = round(cumulative_energy, 2)
            vessel_curve.append(
                {
                    "vesselId": vessel_id,
                    "contractId": series.get("contractId"),
                    "currentSoc": round(
                        float(latest_measurement.get("currentSOC", 0) or 0), 2
                    ),
                    "latestDischargeRateKw": round(
                        float(latest_measurement.get("powerKw", 0) or 0), 2
                    ),
                    "totalEnergyDischargedKwh": round(
                        sum(point["energyDischargedKwh"] for point in points), 2
                    ),
                    "latestTimestamp": (
                        latest_measurement.get("timestamp").isoformat()
                        if latest_measurement.get("timestamp")
                        else None
                    ),
                    "points": points,
                }
            )
        vessel_curve.sort(
            key=lambda item: item["totalEnergyDischargedKwh"], reverse=True
        )

        load_curve = sorted(time_series.values(), key=lambda item: item["timestamp"])
        cumulative_energy = 0.0
        for point in load_curve:
            cumulative_energy += point["energyDischargedKwh"]
            point["cumulativeEnergyDischargedKwh"] = round(cumulative_energy, 2)

        target_energy = (
            float(selected_event.get("targetEnergyKwh", 0) or 0)
            if selected_event
            else 0.0
        )
        progress_percent = (
            round((energy_delivered / target_energy) * 100, 2)
            if target_energy > 0
            else 0.0
        )

        available_events = [
            {
                "id": event["id"],
                "stationId": event["stationId"],
                "status": event["status"],
                "startTime": event["startTime"],
                "endTime": event["endTime"],
                "targetEnergyKwh": event["targetEnergyKwh"],
                "regionLabel": self._region_label(event.get("station") or {}),
            }
            for event in filtered_events
        ]
        available_events.sort(
            key=lambda item: parse_datetime(item["startTime"])
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        return convert_decimals(
            {
                "filters": {
                    "eventId": selected_event_id,
                    "region": region or "",
                    "periodHours": period_hours,
                },
                "selectedEvent": (
                    {
                        "id": selected_event["id"],
                        "stationId": selected_event["stationId"],
                        "status": selected_event["status"],
                        "targetEnergyKwh": selected_event["targetEnergyKwh"],
                        "startTime": selected_event["startTime"],
                        "endTime": selected_event["endTime"],
                        "regionLabel": self._region_label(
                            selected_event.get("station") or {}
                        ),
                    }
                    if selected_event
                    else None
                ),
                "summary": {
                    "totalEnergyDeliveredKwh": round(energy_delivered, 2),
                    "progressPercent": progress_percent,
                    "activeVessels": len(vessel_rates),
                    "eventStatus": (
                        selected_event.get("status") if selected_event else None
                    ),
                    "targetEnergyKwh": round(target_energy, 2),
                },
                "vesselRates": vessel_rates,
                "vesselCurve": vessel_curve,
                "loadCurve": load_curve,
                "baselineAvailable": False,
                "availableEvents": available_events,
                "empty": len(measurements) == 0,
                "updatedAt": now.isoformat(),
            }
        )

    def _region_label(self, station: Dict[str, Any]) -> str:
        parts = [
            station.get("city"),
            station.get("provinceOrState"),
            station.get("country"),
        ]
        return ", ".join([str(part) for part in parts if part])

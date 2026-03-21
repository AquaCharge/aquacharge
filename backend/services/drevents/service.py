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


class ContractRepository(Protocol):
    def list_contracts(self) -> List[Dict[str, Any]]:
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


class DynamoContractRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name=config.CONTRACTS_TABLE, region_name=config.AWS_REGION
        )

    def list_contracts(self) -> List[Dict[str, Any]]:
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
    contract_repository: ContractRepository
    station_repository: StationRepository

    def __init__(
        self,
        event_repository: Optional[DREventRepository] = None,
        measurement_repository: Optional[MeasurementRepository] = None,
        contract_repository: Optional[ContractRepository] = None,
        station_repository: Optional[StationRepository] = None,
    ):
        self.event_repository = event_repository or DynamoDREventRepository()
        self.measurement_repository = (
            measurement_repository or DynamoMeasurementRepository()
        )
        self.contract_repository = contract_repository or DynamoContractRepository()
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

    def get_analytics_snapshot(
        self,
        event_id: Optional[str] = None,
        region: Optional[str] = None,
        period_hours: int = 168,
        grain: str = "day",
    ) -> Dict[str, Any]:
        period_hours = max(1, min(period_hours, 24 * 30))
        normalized_grain = (grain or "day").strip().lower()
        if normalized_grain not in {"hour", "day"}:
            normalized_grain = "day"

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(hours=period_hours)
        normalized_region = (region or "").strip().lower()

        events = self.list_events()
        filtered_events = []
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

            filtered_events.append({**event, "station": station or {}})

        event_ids = {event.get("id") for event in filtered_events if event.get("id")}
        selected_event = None
        if event_id:
            selected_event = next(
                (event for event in filtered_events if event.get("id") == event_id), None
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

        measurements: List[Dict[str, Any]] = []
        for measurement in self.measurement_repository.list_measurements():
            measurement_time = parse_datetime(
                measurement.get("timestamp") or measurement.get("createdAt")
            )
            if measurement_time is None or measurement_time < period_start:
                continue
            measurement_event_id = measurement.get("drEventId")
            if selected_event_id and measurement_event_id != selected_event_id:
                continue
            if not selected_event_id and event_ids and measurement_event_id not in event_ids:
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

        contracts = []
        for contract in self.contract_repository.list_contracts():
            contract_event_id = contract.get("drEventId")
            if selected_event_id and contract_event_id != selected_event_id:
                continue
            if not selected_event_id and event_ids and contract_event_id not in event_ids:
                continue
            contracts.append(contract)

        def _bucket_start(ts: datetime) -> datetime:
            if normalized_grain == "hour":
                return ts.replace(minute=0, second=0, microsecond=0)
            return ts.replace(hour=0, minute=0, second=0, microsecond=0)

        time_buckets: Dict[str, Dict[str, Any]] = {}
        vessel_totals: Dict[str, Dict[str, Any]] = {}
        hourly_heatmap: Dict[tuple, Dict[str, float]] = {}
        total_energy = 0.0
        total_power = 0.0
        for measurement in measurements:
            timestamp = measurement["timestamp"]
            bucket_ts = _bucket_start(timestamp)
            bucket_key = bucket_ts.isoformat()
            bucket = time_buckets.setdefault(
                bucket_key,
                {
                    "timestamp": bucket_key,
                    "energyDischargedKwh": 0.0,
                    "averagePowerKw": 0.0,
                    "samples": 0,
                },
            )
            bucket["energyDischargedKwh"] += measurement["energyKwh"]
            bucket["averagePowerKw"] += measurement["powerKw"]
            bucket["samples"] += 1

            total_energy += measurement["energyKwh"]
            total_power += measurement["powerKw"]

            vessel_id = str(measurement.get("vesselId") or "unknown")
            vessel_entry = vessel_totals.setdefault(
                vessel_id,
                {
                    "vesselId": vessel_id,
                    "contractId": measurement.get("contractId"),
                    "totalEnergyDischargedKwh": 0.0,
                    "latestPowerKw": 0.0,
                    "latestTimestamp": None,
                },
            )
            vessel_entry["totalEnergyDischargedKwh"] += measurement["energyKwh"]
            latest_ts = vessel_entry.get("latestTimestamp")
            if latest_ts is None or timestamp >= latest_ts:
                vessel_entry["latestTimestamp"] = timestamp
                vessel_entry["latestPowerKw"] = measurement["powerKw"]
                if measurement.get("contractId"):
                    vessel_entry["contractId"] = measurement.get("contractId")

            heat_key = (timestamp.weekday(), timestamp.hour)
            heat_entry = hourly_heatmap.setdefault(heat_key, {"powerTotal": 0.0, "samples": 0})
            heat_entry["powerTotal"] += measurement["powerKw"]
            heat_entry["samples"] += 1

        ordered_series = sorted(time_buckets.values(), key=lambda item: item["timestamp"])
        for bucket in ordered_series:
            samples = max(int(bucket.pop("samples", 0)), 1)
            bucket["averagePowerKw"] = round(bucket["averagePowerKw"] / samples, 2)
            bucket["energyDischargedKwh"] = round(bucket["energyDischargedKwh"], 2)

        vessel_leaderboard = sorted(
            [
                {
                    **entry,
                    "totalEnergyDischargedKwh": round(
                        entry["totalEnergyDischargedKwh"], 2
                    ),
                    "latestPowerKw": round(float(entry.get("latestPowerKw", 0.0) or 0.0), 2),
                    "latestTimestamp": (
                        entry["latestTimestamp"].isoformat()
                        if entry.get("latestTimestamp")
                        else None
                    ),
                }
                for entry in vessel_totals.values()
            ],
            key=lambda item: item["totalEnergyDischargedKwh"],
            reverse=True,
        )

        status_counts: Dict[str, int] = {}
        for event in filtered_events:
            status = str(event.get("status") or "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        total_statuses = max(sum(status_counts.values()), 1)
        status_distribution = sorted(
            [
                {
                    "status": status,
                    "count": count,
                    "percent": round((count / total_statuses) * 100, 2),
                }
                for status, count in status_counts.items()
            ],
            key=lambda item: item["count"],
            reverse=True,
        )

        finalized_contracts = [
            contract
            for contract in contracts
            if str(contract.get("status") or "").lower()
            in {"completed", "failed", "cancelled"}
        ]
        completed_contracts = [
            contract
            for contract in finalized_contracts
            if str(contract.get("status") or "").lower() == "completed"
        ]
        completion_rate = (
            (len(completed_contracts) / len(finalized_contracts)) * 100
            if finalized_contracts
            else 0.0
        )

        max_participants = sum(
            int(float(event.get("maxParticipants", 0) or 0)) for event in filtered_events
        )
        participation_rate = (
            (len(vessel_totals) / max_participants) * 100 if max_participants > 0 else 0.0
        )

        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        bands = [(0, 4, "00-04"), (4, 8, "04-08"), (8, 12, "08-12"), (12, 18, "12-18"), (18, 24, "18-24")]
        heatmap = []
        for day_index, day_label in enumerate(day_labels):
            row = []
            for band_start, band_end, band_label in bands:
                power_total = 0.0
                samples = 0
                for hour in range(band_start, band_end):
                    entry = hourly_heatmap.get((day_index, hour))
                    if entry:
                        power_total += entry["powerTotal"]
                        samples += int(entry["samples"])
                row.append(
                    {
                        "label": band_label,
                        "averagePowerKw": round(power_total / samples, 2) if samples else 0.0,
                    }
                )
            heatmap.append({"dayLabel": day_label, "bands": row})

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

        # --- Financials ---
        total_payout_usd = 0.0
        committed_exposure_usd = 0.0
        financial_time_buckets: Dict[str, float] = {}
        event_payout_map: Dict[str, float] = {}

        for contract in contracts:
            contract_status = str(contract.get("status") or "").lower()
            contract_value = float(contract.get("totalValue") or 0)
            if contract_status == "completed":
                total_payout_usd += contract_value
                end_time = parse_datetime(contract.get("endTime"))
                if end_time:
                    bucket_ts = _bucket_start(end_time)
                    bucket_key = bucket_ts.isoformat()
                    financial_time_buckets[bucket_key] = (
                        financial_time_buckets.get(bucket_key, 0.0) + contract_value
                    )
                contract_event_id = contract.get("drEventId") or ""
                event_payout_map[contract_event_id] = (
                    event_payout_map.get(contract_event_id, 0.0) + contract_value
                )
            elif contract_status in ("pending", "active"):
                committed_exposure_usd += contract_value

        cost_per_kwh_usd = (
            round(total_payout_usd / total_energy, 4)
            if total_payout_usd > 0 and total_energy > 0
            else None
        )

        weighted_price_sum = 0.0
        weighted_price_total_kwh = 0.0
        for event in filtered_events:
            target_kwh = float(event.get("targetEnergyKwh") or 0)
            price = float(event.get("pricePerKwh") or 0)
            if target_kwh > 0:
                weighted_price_sum += price * target_kwh
                weighted_price_total_kwh += target_kwh
        avg_price_per_kwh_usd = (
            round(weighted_price_sum / weighted_price_total_kwh, 4)
            if weighted_price_total_kwh > 0
            else None
        )

        financial_series = [
            {"timestamp": ts, "payoutUsd": round(payout, 2)}
            for ts, payout in sorted(financial_time_buckets.items())
        ]

        event_breakdown = []
        for event in filtered_events:
            ev_id = event.get("id") or ""
            target_kwh = float(event.get("targetEnergyKwh") or 0)
            price = float(event.get("pricePerKwh") or 0)
            target_value = round(target_kwh * price, 2)
            actual_payout = round(event_payout_map.get(ev_id, 0.0), 2)
            delivery_rate = (
                round((actual_payout / target_value) * 100, 2) if target_value > 0 else 0.0
            )
            event_breakdown.append(
                {
                    "eventId": ev_id,
                    "startTime": event.get("startTime"),
                    "targetValueUsd": target_value,
                    "actualPayoutUsd": actual_payout,
                    "deliveryRatePct": delivery_rate,
                }
            )
        event_breakdown.sort(
            key=lambda item: parse_datetime(item["startTime"])
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        financials = {
            "totalPayoutUsd": round(total_payout_usd, 2),
            "committedExposureUsd": round(committed_exposure_usd, 2),
            "costPerKwhUsd": cost_per_kwh_usd,
            "avgPricePerKwhUsd": avg_price_per_kwh_usd,
            "timeSeries": financial_series,
            "eventBreakdown": event_breakdown,
        }

        return convert_decimals(
            {
                "filters": {
                    "eventId": selected_event_id,
                    "region": region or "",
                    "periodHours": period_hours,
                    "grain": normalized_grain,
                },
                "summary": {
                    "totalEnergyDischargedKwh": round(total_energy, 2),
                    "averagePowerKw": round(total_power / len(measurements), 2)
                    if measurements
                    else 0.0,
                    "peakPowerKw": round(
                        max(
                            (
                                float(point.get("averagePowerKw", 0) or 0)
                                for point in ordered_series
                            ),
                            default=0.0,
                        ),
                        2,
                    ),
                    "completionRatePercent": round(completion_rate, 2),
                    "participationRatePercent": round(participation_rate, 2),
                    "eventsConsidered": len(filtered_events),
                    "contractsConsidered": len(contracts),
                    "baselineAvailable": False,
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
                "timeSeries": ordered_series,
                "statusDistribution": status_distribution,
                "vesselLeaderboard": vessel_leaderboard,
                "heatmap": heatmap,
                "availableEvents": available_events,
                "financials": financials,
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

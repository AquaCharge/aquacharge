from datetime import datetime
from time import perf_counter
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Protocol, Tuple

try:
    from geopy.distance import geodesic
except ModuleNotFoundError:
    geodesic = None

from db.dynamoClient import DynamoClient

DEFAULT_KWH_PER_KM = 0.2


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_distance_meters(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    earth_radius_meters = 6371000.0
    lat_delta = radians(end_lat - start_lat)
    lon_delta = radians(end_lon - start_lon)

    origin_lat_radians = radians(start_lat)
    destination_lat_radians = radians(end_lat)

    a_term = (
        sin(lat_delta / 2) ** 2
        + cos(origin_lat_radians)
        * cos(destination_lat_radians)
        * sin(lon_delta / 2) ** 2
    )
    c_term = 2 * asin(sqrt(a_term))
    return earth_radius_meters * c_term


def _distance_meters(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    if geodesic is not None:
        try:
            return float(geodesic((start_lat, start_lon), (end_lat, end_lon)).meters)
        except Exception:
            pass
    return _haversine_distance_meters(start_lat, start_lon, end_lat, end_lon)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _derive_soc_from_capacity(vessel: Dict[str, Any]) -> Optional[float]:
    capacity_kwh = _to_float(vessel.get("capacity"))
    max_capacity_kwh = _to_float(vessel.get("maxCapacity"))
    if (
        capacity_kwh is None
        or max_capacity_kwh is None
        or max_capacity_kwh <= 0
    ):
        return None

    soc_percent = (capacity_kwh / max_capacity_kwh) * 100.0
    return max(0.0, min(100.0, soc_percent))


class VesselRepository(Protocol):
    def list_vessels(self) -> List[Dict[str, Any]]:
        pass


class StationRepository(Protocol):
    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        pass


class MeasurementRepository(Protocol):
    def get_latest_soc(self, vessel_id: str) -> Optional[float]:
        pass


class DynamoVesselRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-vessels-dev", region_name="us-east-1"
        )

    def list_vessels(self) -> List[Dict[str, Any]]:
        return self.client.scan_items()


class DynamoStationRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-stations-dev", region_name="us-east-1"
        )

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        station = self.client.get_item({"id": station_id})
        return station or None


class DynamoMeasurementRepository:
    def __init__(self, client: Optional[DynamoClient] = None):
        self.client = client or DynamoClient(
            table_name="aquacharge-measurements-dev", region_name="us-east-1"
        )
        self._latest_soc_by_vessel_id: Optional[Dict[str, Tuple[str, float]]] = None

    def _build_soc_cache(self) -> None:
        if self._latest_soc_by_vessel_id is not None:
            return

        self._latest_soc_by_vessel_id = {}
        try:
            measurements = self.client.scan_items()
        except Exception:
            measurements = []

        for measurement in measurements:
            vessel_id = measurement.get("vesselId")
            if not vessel_id:
                continue

            soc = _to_float(measurement.get("currentSOC"))
            if soc is None:
                continue

            timestamp = str(
                measurement.get("timestamp") or measurement.get("createdAt") or ""
            )

            current_best = self._latest_soc_by_vessel_id.get(vessel_id)
            if current_best is None or timestamp >= current_best[0]:
                self._latest_soc_by_vessel_id[vessel_id] = (timestamp, soc)

    def get_latest_soc(self, vessel_id: str) -> Optional[float]:
        self._build_soc_cache()
        if self._latest_soc_by_vessel_id is None:
            return None

        latest = self._latest_soc_by_vessel_id.get(vessel_id)
        return None if latest is None else latest[1]


class EligibilityService:
    def __init__(
        self,
        vessel_repository: Optional[VesselRepository] = None,
        station_repository: Optional[StationRepository] = None,
        measurement_repository: Optional[MeasurementRepository] = None,
    ):
        self.vessel_repository = vessel_repository or DynamoVesselRepository()
        self.station_repository = station_repository or DynamoStationRepository()
        self.measurement_repository = (
            measurement_repository or DynamoMeasurementRepository()
        )

    def evaluate_vessels_for_event(
        self,
        dr_event: Dict[str, Any],
        include_ineligible: bool = False,
    ) -> Dict[str, Any]:
        started_at = perf_counter()
        station_id = dr_event.get("stationId")
        if not station_id:
            raise ValueError("DR event must include stationId")

        station = self.station_repository.get_station(station_id)
        if not station:
            raise LookupError("Station not found")

        vessels = self.vessel_repository.list_vessels()
        vessel_results: List[Dict[str, Any]] = []
        for vessel in vessels:
            vessel_result = self._evaluate_single_vessel(vessel, station, dr_event)
            if include_ineligible or vessel_result["eligible"]:
                vessel_results.append(vessel_result)

        vessel_results.sort(
            key=lambda result: (
                0 if result["eligible"] else 1,
                (
                    result["distanceMeters"]
                    if result["distanceMeters"] is not None
                    else float("inf")
                ),
            )
        )

        eligible_count = len(
            [result for result in vessel_results if result["eligible"]]
        )
        duration_ms = round((perf_counter() - started_at) * 1000.0, 2)
        return {
            "eventId": dr_event.get("id"),
            "stationId": station_id,
            "totalVesselsEvaluated": len(vessels),
            "eligibleCount": eligible_count,
            "evaluationDurationMs": duration_ms,
            "vessels": vessel_results,
        }

    def _evaluate_single_vessel(
        self,
        vessel: Dict[str, Any],
        station: Dict[str, Any],
        dr_event: Dict[str, Any],
    ) -> Dict[str, Any]:
        rejection_reasons: List[str] = []

        vessel_latitude = _to_float(vessel.get("latitude"))
        vessel_longitude = _to_float(vessel.get("longitude"))
        station_latitude = _to_float(station.get("latitude"))
        station_longitude = _to_float(station.get("longitude"))
        vessel_range_meters = _to_float(vessel.get("rangeMeters")) or 0.0

        distance_meters: Optional[float] = None
        distance_km: Optional[float] = None
        if None in (
            vessel_latitude,
            vessel_longitude,
            station_latitude,
            station_longitude,
        ):
            rejection_reasons.append("Missing vessel or station coordinates")
        else:
            distance_meters = _distance_meters(
                vessel_latitude,
                vessel_longitude,
                station_latitude,
                station_longitude,
            )
            distance_km = distance_meters / 1000.0
            if distance_meters > vessel_range_meters:
                rejection_reasons.append("Vessel is outside operational range")

        if vessel.get("active") is False:
            rejection_reasons.append("Vessel is inactive")

        event_details = dr_event.get("details") or {}
        required_charger_type = event_details.get("requiredChargerType")
        vessel_charger_type = vessel.get("chargerType")
        if required_charger_type and vessel_charger_type != required_charger_type:
            rejection_reasons.append("Vessel charger type is incompatible")

        minimum_soc = _to_float(event_details.get("minimumSoc"))
        if minimum_soc is None:
            minimum_soc = 20.0

        current_soc = self.measurement_repository.get_latest_soc(vessel.get("id"))
        if current_soc is None:
            current_soc = _to_float(vessel.get("currentSoc"))
        if current_soc is None:
            current_soc = _derive_soc_from_capacity(vessel)

        consumption_kwh_per_km = _to_float(event_details.get("kwhPerKm"))
        if consumption_kwh_per_km is None:
            consumption_kwh_per_km = _to_float(vessel.get("kwhPerKm"))
        if consumption_kwh_per_km is None:
            consumption_kwh_per_km = DEFAULT_KWH_PER_KM

        forecasted_soc: Optional[float] = None
        if current_soc is not None and distance_km is not None:
            forecasted_soc = current_soc - (distance_km * consumption_kwh_per_km)
            forecasted_soc = max(0.0, min(100.0, forecasted_soc))

        vessel_capacity_kwh = _to_float(vessel.get("capacity")) or 0.0
        available_battery_kwh: Optional[float] = None
        if forecasted_soc is not None:
            available_battery_kwh = vessel_capacity_kwh * (forecasted_soc / 100.0)

        required_energy_per_vessel_kwh: Optional[float] = _to_float(
            event_details.get("requiredEnergyPerVesselKwh")
        )
        if required_energy_per_vessel_kwh is None:
            target_energy_kwh = _to_float(dr_event.get("targetEnergyKwh"))
            max_participants = _to_float(dr_event.get("maxParticipants"))
            if (
                target_energy_kwh is not None
                and max_participants
                and max_participants > 0
            ):
                required_energy_per_vessel_kwh = target_energy_kwh / max_participants

        if required_energy_per_vessel_kwh is not None:
            if available_battery_kwh is None:
                rejection_reasons.append("Unable to compute available battery capacity")
            elif available_battery_kwh < required_energy_per_vessel_kwh:
                rejection_reasons.append("Insufficient available battery capacity")

        schedule_compatible = self._is_schedule_compatible(vessel, dr_event)
        if not schedule_compatible:
            rejection_reasons.append("Vessel schedule is incompatible")

        if current_soc is None:
            rejection_reasons.append("Missing SOC telemetry")
        elif forecasted_soc is not None and forecasted_soc < minimum_soc:
            rejection_reasons.append("SOC below event minimum")

        return {
            "vesselId": vessel.get("id"),
            "displayName": vessel.get("displayName"),
            "eligible": len(rejection_reasons) == 0,
            "reasons": rejection_reasons,
            "distanceMeters": distance_meters,
            "distanceKm": distance_km,
            "rangeMeters": vessel_range_meters,
            "currentSoc": current_soc,
            "forecastedSoc": forecasted_soc,
            "kwhPerKm": consumption_kwh_per_km,
            "availableBatteryKwh": available_battery_kwh,
            "requiredEnergyPerVesselKwh": required_energy_per_vessel_kwh,
            "scheduleCompatible": schedule_compatible,
            "minimumSoc": minimum_soc,
            "chargerType": vessel_charger_type,
        }

    def _is_schedule_compatible(
        self,
        vessel: Dict[str, Any],
        dr_event: Dict[str, Any],
    ) -> bool:
        event_start = _parse_datetime(dr_event.get("startTime"))
        event_end = _parse_datetime(dr_event.get("endTime"))

        if event_start is None or event_end is None:
            return True

        available_from = _parse_datetime(
            vessel.get("availableFrom") or vessel.get("availableStart")
        )
        available_until = _parse_datetime(
            vessel.get("availableUntil") or vessel.get("availableEnd")
        )

        if available_from and event_start < available_from:
            return False
        if available_until and event_end > available_until:
            return False
        return True

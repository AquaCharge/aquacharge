from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Protocol

from boto3.dynamodb.conditions import Attr

from db.dynamoClient import DynamoClient


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

    def get_latest_soc(self, vessel_id: str) -> Optional[float]:
        try:
            measurements = self.client.scan_items(
                filter_expression=Attr("vesselId").eq(vessel_id)
            )
        except Exception:
            return None

        if not measurements:
            return None

        latest_measurement = max(
            measurements,
            key=lambda measurement: measurement.get("timestamp", ""),
        )
        return _to_float(latest_measurement.get("currentSOC"))


class EligibilityService:
    def __init__(
        self,
        vessel_repository: Optional[VesselRepository] = None,
        station_repository: Optional[StationRepository] = None,
        measurement_repository: Optional[MeasurementRepository] = None,
    ):
        self.vessel_repository = vessel_repository or DynamoVesselRepository()
        self.station_repository = station_repository or DynamoStationRepository()
        self.measurement_repository = measurement_repository or DynamoMeasurementRepository()

    def evaluate_vessels_for_event(
        self,
        dr_event: Dict[str, Any],
        include_ineligible: bool = False,
    ) -> Dict[str, Any]:
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
                result["distanceMeters"] if result["distanceMeters"] is not None else float("inf"),
            )
        )

        eligible_count = len([result for result in vessel_results if result["eligible"]])
        return {
            "eventId": dr_event.get("id"),
            "stationId": station_id,
            "totalVesselsEvaluated": len(vessels),
            "eligibleCount": eligible_count,
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
        if None in (vessel_latitude, vessel_longitude, station_latitude, station_longitude):
            rejection_reasons.append("Missing vessel or station coordinates")
        else:
            distance_meters = _haversine_distance_meters(
                vessel_latitude,
                vessel_longitude,
                station_latitude,
                station_longitude,
            )
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
            rejection_reasons.append("Missing SOC telemetry")
        elif current_soc < minimum_soc:
            rejection_reasons.append("SOC below event minimum")

        return {
            "vesselId": vessel.get("id"),
            "displayName": vessel.get("displayName"),
            "eligible": len(rejection_reasons) == 0,
            "reasons": rejection_reasons,
            "distanceMeters": distance_meters,
            "rangeMeters": vessel_range_meters,
            "currentSoc": current_soc,
            "minimumSoc": minimum_soc,
            "chargerType": vessel_charger_type,
        }

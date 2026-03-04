from services.eligibility.service import EligibilityService


class InMemoryVesselRepository:
    def __init__(self, vessels):
        self._vessels = vessels

    def list_vessels(self):
        return self._vessels


class InMemoryStationRepository:
    def __init__(self, stations):
        self._stations = stations

    def get_station(self, station_id):
        return self._stations.get(station_id)


class InMemoryMeasurementRepository:
    def __init__(self, soc_by_vessel_id):
        self._soc_by_vessel_id = soc_by_vessel_id

    def get_latest_soc(self, vessel_id):
        return self._soc_by_vessel_id.get(vessel_id)


def _build_service(vessels, stations, soc_by_vessel_id):
    return EligibilityService(
        vessel_repository=InMemoryVesselRepository(vessels),
        station_repository=InMemoryStationRepository(stations),
        measurement_repository=InMemoryMeasurementRepository(soc_by_vessel_id),
    )


def test_evaluate_vessels_for_event_returns_only_eligible_by_default():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Near Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 5000,
            "chargerType": "Type 2 AC",
        },
        {
            "id": "v-2",
            "displayName": "Far Vessel",
            "active": True,
            "latitude": 45.0,
            "longitude": -64.0,
            "rangeMeters": 1000,
            "chargerType": "Type 2 AC",
        },
    ]
    stations = {"station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}}
    soc_by_vessel_id = {"v-1": 80.0, "v-2": 80.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {"id": "event-1", "stationId": "station-1", "details": {"minimumSoc": 30}}

    result = service.evaluate_vessels_for_event(dr_event)

    assert result["totalVesselsEvaluated"] == 2
    assert result["eligibleCount"] == 1
    assert len(result["vessels"]) == 1
    assert result["vessels"][0]["vesselId"] == "v-1"


def test_evaluate_vessels_for_event_can_include_ineligible_results():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Low SOC Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 5000,
            "chargerType": "Type 2 AC",
        }
    ]
    stations = {"station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}}
    soc_by_vessel_id = {"v-1": 10.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {"id": "event-1", "stationId": "station-1", "details": {"minimumSoc": 30}}

    result = service.evaluate_vessels_for_event(dr_event, include_ineligible=True)

    assert result["eligibleCount"] == 0
    assert len(result["vessels"]) == 1
    assert result["vessels"][0]["eligible"] is False
    assert "SOC below event minimum" in result["vessels"][0]["reasons"]


def test_evaluate_vessels_for_event_validates_charger_compatibility():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Mismatched Charger Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 5000,
            "chargerType": "CCS",
        }
    ]
    stations = {"station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}}
    soc_by_vessel_id = {"v-1": 80.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {"minimumSoc": 20, "requiredChargerType": "Type 2 AC"},
    }

    result = service.evaluate_vessels_for_event(dr_event, include_ineligible=True)

    assert result["vessels"][0]["eligible"] is False
    assert "Vessel charger type is incompatible" in result["vessels"][0]["reasons"]


def test_evaluate_vessels_for_event_requires_station():
    service = _build_service(
        vessels=[],
        stations={},
        soc_by_vessel_id={},
    )

    try:
        service.evaluate_vessels_for_event({"id": "event-1", "stationId": "missing-station"})
        assert False, "Expected LookupError"
    except LookupError as error:
        assert str(error) == "Station not found"


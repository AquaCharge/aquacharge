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
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {"v-1": 80.0, "v-2": 80.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {"minimumSoc": 30},
    }

    result = service.evaluate_vessels_for_event(dr_event)

    assert result["totalVesselsEvaluated"] == 2
    assert result["eligibleCount"] == 1
    assert len(result["vessels"]) == 1
    assert result["vessels"][0]["vesselId"] == "v-1"
    assert result["vessels"][0]["forecastedSoc"] is not None


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
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {"v-1": 10.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {"minimumSoc": 30},
    }

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
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
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
        service.evaluate_vessels_for_event(
            {"id": "event-1", "stationId": "missing-station"}
        )
        assert False, "Expected LookupError"
    except LookupError as error:
        assert str(error) == "Station not found"


def test_forecasted_soc_calculation_uses_distance_and_kwh_per_km():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Forecast Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 100000,
            "chargerType": "Type 2 AC",
            "capacity": 100.0,
        }
    ]
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {"v-1": 80.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {"minimumSoc": 20, "kwhPerKm": 0.5},
    }

    result = service.evaluate_vessels_for_event(dr_event)
    vessel_result = result["vessels"][0]

    expected_forecast = 80.0 - (vessel_result["distanceKm"] * 0.5)
    assert vessel_result["forecastedSoc"] == expected_forecast


def test_schedule_compatibility_marks_vessel_ineligible_when_window_mismatches():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Schedule Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 100000,
            "chargerType": "Type 2 AC",
            "capacity": 150.0,
            "availableFrom": "2026-03-05T12:00:00",
            "availableUntil": "2026-03-05T13:00:00",
        }
    ]
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {"v-1": 75.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "startTime": "2026-03-05T10:00:00",
        "endTime": "2026-03-05T11:00:00",
        "details": {"minimumSoc": 20, "requiredEnergyPerVesselKwh": 5},
    }

    result = service.evaluate_vessels_for_event(dr_event, include_ineligible=True)
    vessel_result = result["vessels"][0]

    assert vessel_result["scheduleCompatible"] is False
    assert vessel_result["eligible"] is False
    assert "Vessel schedule is incompatible" in vessel_result["reasons"]


def test_available_battery_capacity_check_blocks_insufficient_vessels():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Small Battery Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 100000,
            "chargerType": "Type 2 AC",
            "capacity": 10.0,
            "maxCapacity": 10.0,
        }
    ]
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {"v-1": 50.0}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {
            "minimumSoc": 20,
            "kwhPerKm": 0.1,
            "requiredEnergyPerVesselKwh": 8.0,
        },
    }

    result = service.evaluate_vessels_for_event(dr_event, include_ineligible=True)
    vessel_result = result["vessels"][0]

    assert vessel_result["eligible"] is False
    assert "Insufficient available battery capacity" in vessel_result["reasons"]


def test_eligibility_derives_soc_from_capacity_when_telemetry_is_missing():
    vessels = [
        {
            "id": "v-1",
            "displayName": "Derived SOC Vessel",
            "active": True,
            "latitude": 44.65,
            "longitude": -63.57,
            "rangeMeters": 100000,
            "chargerType": "Type 2 AC",
            "capacity": 97.0,
            "maxCapacity": 100.0,
        }
    ]
    stations = {
        "station-1": {"id": "station-1", "latitude": 44.651, "longitude": -63.58}
    }
    soc_by_vessel_id = {}

    service = _build_service(vessels, stations, soc_by_vessel_id)
    dr_event = {
        "id": "event-1",
        "stationId": "station-1",
        "details": {"minimumSoc": 20, "requiredEnergyPerVesselKwh": 5.0},
    }

    result = service.evaluate_vessels_for_event(dr_event)
    vessel_result = result["vessels"][0]

    assert vessel_result["eligible"] is True
    assert vessel_result["currentSoc"] == 97.0

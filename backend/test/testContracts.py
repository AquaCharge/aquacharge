"""
Tests for SCRUM-169: contract dispatch and VO accept/decline flow.
Uses in-memory stub repositories — no DynamoDB calls.
"""

import pytest
import jwt
from flask import Flask
from datetime import datetime, timedelta
from api.contracts import contracts_bp
from api.drevents import drevents_bp
from services.contracts.service import ContractService, ContractServiceError
from models.contract import ContractStatus
from config import JWT_SECRET, JWT_ALGORITHM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contract(status="pending", vessel_id="vessel-abc"):
    return {
        "id": "contract-001",
        "vesselId": vessel_id,
        "drEventId": "dr-001",
        "vesselName": "Test Ferry",
        "energyAmount": 100.0,
        "pricePerKwh": 0.15,
        "totalValue": 15.0,
        "startTime": "2026-03-10T08:00:00",
        "endTime": "2026-03-10T12:00:00",
        "status": status,
        "terms": "Standard terms",
        "committedPowerKw": None,
        "operatorNotes": "",
        "acceptedAt": None,
        "createdAt": "2026-03-07T00:00:00",
        "updatedAt": None,
        "createdBy": "pso-user",
        "bookingId": None,
    }


# ---------------------------------------------------------------------------
# Flask test client with mocked JWT
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    flask_app.register_blueprint(contracts_bp, url_prefix="/api/contracts")
    flask_app.register_blueprint(drevents_bp, url_prefix="/api/drevents")
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def _auth_headers():
    """Return a fake Bearer token header."""
    return {"Authorization": "Bearer fake-token"}


def _jwt_headers(user_id="user-vo-001", role=2, user_type=1):
    token = jwt.encode(
        {
            "id": user_id,
            "role": role,
            "type": user_type,
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _mock_jwt_payload(user_id="user-vo-001"):
    return {
        "id": user_id,
        "role": 2,
        "type": 1,
        "role_name": "USER",
        "type_name": "VESSEL_OPERATOR",
    }


# ---------------------------------------------------------------------------
# Service-layer unit tests (no HTTP, no mocking middleware)
# ---------------------------------------------------------------------------


class InMemoryContractRepo:
    """Minimal in-memory repository for service unit tests."""

    def __init__(self, contracts=None):
        self._store = {c["id"]: dict(c) for c in (contracts or [])}

    def list_contracts(self):
        return list(self._store.values())

    def get_contract(self, contract_id):
        return self._store.get(contract_id)

    def create_contract(self, contract_data):
        self._store[contract_data["id"]] = contract_data

    def update_contract(self, contract_id, update_data):
        self._store[contract_id].update(update_data)
        return self._store[contract_id]

    def delete_contract(self, contract_id):
        self._store.pop(contract_id, None)


class _StubBookingRepo:
    def list_bookings(self):
        return []

    def create_booking(self, data):
        pass


class _StubVesselRepo:
    def get_vessel(self, vessel_id):
        return {
            "id": vessel_id,
            "userId": "user-001",
            "chargerType": "AC",
            "maxDischargeRate": 50,
        }


class _StubDREventRepo:
    def get_event(self, event_id):
        return {
            "id": event_id,
            "stationId": "station-xyz",
            "startTime": "2026-03-10T08:00:00+00:00",
            "endTime": "2026-03-10T12:00:00+00:00",
            "status": "Dispatched",
        }

    def update_event(self, event_id, update_data):
        event = self.get_event(event_id)
        event.update(update_data)
        return event


class TestAcceptContract:
    def test_accept_pending_contract_stays_pending_until_booking(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(
            repository=repo,
            booking_repository=_StubBookingRepo(),
            vessel_repository=_StubVesselRepo(),
            drevent_repository=_StubDREventRepo(),
        )

        result = service.accept_contract(
            "contract-001",
            caller_vessel_ids=["vessel-abc"],
            acceptance_data={"committedPowerKw": 25},
        )

        assert result["status"] == ContractStatus.PENDING.value
        assert result["committedPowerKw"] == 25
        assert result["energyAmount"] == pytest.approx(25.0)
        assert float(result["totalValue"]) == pytest.approx(3.75)

    def test_accept_rejects_when_vessel_not_owned(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-other"],
                acceptance_data={"committedPowerKw": 25},
            )

        assert exc_info.value.status_code == 403

    def test_accept_rejects_non_pending_contract(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="active", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 25},
            )

        assert exc_info.value.status_code == 400

    def test_accept_rejects_completed_contract(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="completed", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 25},
            )

        assert exc_info.value.status_code == 400

    def test_accept_missing_contract_returns_404(self):
        repo = InMemoryContractRepo([])
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "does-not-exist",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 25},
            )

        assert exc_info.value.status_code == 404

    def test_accept_requires_committed_power_kw(self):
        repo = InMemoryContractRepo([_make_contract(status="pending", vessel_id="vessel-abc")])
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])

        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "committedPowerKw is required"

    def test_accept_rejects_when_pre_validation_fails(self, monkeypatch):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(
            repository=repo,
            booking_repository=_StubBookingRepo(),
            vessel_repository=_StubVesselRepo(),
            drevent_repository=_StubDREventRepo(),
        )

        def _raise_pre_validation_error(vessel):
            raise ValueError("Vessel vessel-abc has 3 failed contracts (max 3). Ineligible for DR participation.")

        monkeypatch.setattr(
            "services.contracts.service.validation.pre_event_contract_validation",
            _raise_pre_validation_error,
        )

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract(
                "contract-001",
                caller_vessel_ids=["vessel-abc"],
                acceptance_data={"committedPowerKw": 25},
            )

        assert exc_info.value.status_code == 409
        assert "failed contracts" in exc_info.value.message


class TestDeclineContract:
    def test_decline_pending_contract_transitions_to_cancelled(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        result = service.decline_contract(
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )

        assert result["status"] == ContractStatus.CANCELLED.value

    def test_decline_rejects_when_vessel_not_owned(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.decline_contract("contract-001", caller_vessel_ids=["vessel-xyz"])

        assert exc_info.value.status_code == 403

    def test_decline_rejects_non_pending_contract(self):
        for bad_status in ("active", "completed", "cancelled"):
            repo = InMemoryContractRepo(
                [_make_contract(status=bad_status, vessel_id="vessel-abc")]
            )
            service = ContractService(repository=repo)

            with pytest.raises(ContractServiceError) as exc_info:
                service.decline_contract(
                    "contract-001", caller_vessel_ids=["vessel-abc"]
                )

            assert exc_info.value.status_code == 400

    def test_decline_missing_contract_returns_404(self):
        repo = InMemoryContractRepo([])
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.decline_contract("does-not-exist", caller_vessel_ids=["vessel-abc"])

        assert exc_info.value.status_code == 404


class TestListContractsByVessel:
    def test_filters_by_vessel_id(self):
        contracts = [
            _make_contract(status="pending", vessel_id="vessel-abc"),
            {
                **_make_contract(status="active", vessel_id="vessel-xyz"),
                "id": "contract-002",
            },
        ]
        repo = InMemoryContractRepo(contracts)
        service = ContractService(repository=repo)

        result = service.list_contracts(vessel_id="vessel-abc")

        assert len(result) == 1
        assert result[0]["vesselId"] == "vessel-abc"

    def test_filters_by_status(self):
        contracts = [
            _make_contract(status="pending", vessel_id="vessel-abc"),
            {
                **_make_contract(status="active", vessel_id="vessel-abc"),
                "id": "contract-002",
            },
        ]
        repo = InMemoryContractRepo(contracts)
        service = ContractService(repository=repo)

        result = service.list_contracts(status_filter="active", vessel_id="vessel-abc")

        assert len(result) == 1
        assert result[0]["status"] == "active"

    def test_returns_empty_for_unknown_vessel(self):
        repo = InMemoryContractRepo([_make_contract()])
        service = ContractService(repository=repo)

        result = service.list_contracts(vessel_id="vessel-nobody")

        assert result == []


# ---------------------------------------------------------------------------
# HTTP endpoint tests (mock middleware + service)
# ---------------------------------------------------------------------------


class TestAcceptEndpoint:
    def test_accept_returns_401_without_token(self, client):
        """Without a valid JWT the endpoint must reject with 401."""
        rv = client.post("/api/contracts/contract-001/accept")
        assert rv.status_code == 401

    def test_decline_returns_401_without_token(self, client):
        """Without a valid JWT the decline endpoint must reject with 401."""
        rv = client.post("/api/contracts/contract-001/decline")
        assert rv.status_code == 401

    def test_my_contracts_returns_401_without_token(self, client):
        """Without a valid JWT the my-contracts endpoint must reject with 401."""
        rv = client.get("/api/contracts/my-contracts")
        assert rv.status_code == 401

    def test_accept_endpoint_exists(self, app):
        rules = [str(r) for r in app.url_map.iter_rules()]
        assert any("accept" in r for r in rules)

    def test_decline_endpoint_exists(self, app):
        rules = [str(r) for r in app.url_map.iter_rules()]
        assert any("decline" in r for r in rules)

    def test_my_contracts_endpoint_exists(self, app):
        rules = [str(r) for r in app.url_map.iter_rules()]
        assert any("my-contracts" in r for r in rules)

    def test_dispatch_accepts_power_operator_token_without_type_name(self, client, monkeypatch):
        import api.drevents as drevents_api

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {
                "id": event_id,
                "stationId": "station-xyz",
                "maxParticipants": 1,
                "status": "Created",
            },
        )
        monkeypatch.setattr(
            drevents_api.eligibility_service,
            "evaluate_vessels_for_event",
            lambda event, include_ineligible=False: {
                "vessels": [{"vesselId": "vessel-abc", "displayName": "Sea Breeze"}]
            },
        )
        monkeypatch.setattr(
            drevents_api.contract_service,
            "dispatch_event",
            lambda dr_event, eligible_vessels, caller_user_id: [{"id": "contract-001"}],
        )
        monkeypatch.setattr(
            drevents_api.drevent_service,
            "update_event",
            lambda event_id, update_data: {
                "id": event_id,
                "status": update_data["status"],
            },
        )

        rv = client.post(
            "/api/drevents/dr-001/dispatch",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 200
        assert rv.get_json()["contractsCreated"] == 1

    def test_dispatch_rejects_vessel_operator_token(self, client):
        rv = client.post(
            "/api/drevents/dr-001/dispatch",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
        )

        assert rv.status_code == 403
        assert "power operators" in rv.get_json()["error"].lower()

    def test_create_drevent_rejects_vessel_operator_token(self, client):
        rv = client.post(
            "/api/drevents",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
            json={
                "stationId": "station-1",
                "targetEnergyKwh": 100,
                "pricePerKwh": 0.25,
                "startTime": "2026-03-21T10:00:00+00:00",
                "endTime": "2026-03-21T12:00:00+00:00",
                "maxParticipants": 2,
            },
        )

        assert rv.status_code == 403
        assert "power operators" in rv.get_json()["error"].lower()

    def test_my_contracts_hides_pending_contracts_that_are_no_longer_eligible(
        self, client, monkeypatch
    ):
        import api.contracts as contracts_api

        monkeypatch.setattr(
            contracts_api,
            "_get_owned_vessel_ids",
            lambda user_id: ["vessel-abc"],
        )
        monkeypatch.setattr(
            contracts_api.contract_service,
            "list_contracts",
            lambda status_filter=None, vessel_id=None: [
                _make_contract(status="pending", vessel_id="vessel-abc"),
                {
                    **_make_contract(status="active", vessel_id="vessel-abc"),
                    "id": "contract-002",
                },
            ],
        )
        monkeypatch.setattr(
            contracts_api,
            "_get_current_eligibility",
            lambda contract: {"eligible": False, "reasons": ["Vessel moved out of range"]},
        )

        rv = client.get(
            "/api/contracts/my-contracts",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
        )

        assert rv.status_code == 200
        payload = rv.get_json()
        assert len(payload) == 1
        assert payload[0]["status"] == "active"

    def test_my_contracts_keeps_accepted_pending_contracts_visible(
        self, client, monkeypatch
    ):
        import api.contracts as contracts_api

        monkeypatch.setattr(
            contracts_api,
            "_get_owned_vessel_ids",
            lambda user_id: ["vessel-abc"],
        )
        monkeypatch.setattr(
            contracts_api.contract_service,
            "list_contracts",
            lambda status_filter=None, vessel_id=None: [
                {
                    **_make_contract(status="pending", vessel_id="vessel-abc"),
                    "acceptedAt": "2026-03-10T07:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(
            contracts_api,
            "_get_current_eligibility",
            lambda contract: {"eligible": False, "reasons": ["Vessel moved out of range"]},
        )

        rv = client.get(
            "/api/contracts/my-contracts",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
        )

        assert rv.status_code == 200
        payload = rv.get_json()
        assert len(payload) == 1
        assert payload[0]["acceptedAt"] == "2026-03-10T07:00:00+00:00"

    def test_accept_rejects_when_pending_contract_is_no_longer_eligible(
        self, client, monkeypatch
    ):
        import api.contracts as contracts_api

        monkeypatch.setattr(
            contracts_api,
            "_get_owned_vessel_ids",
            lambda user_id: ["vessel-abc"],
        )
        monkeypatch.setattr(
            contracts_api.contract_service,
            "get_contract",
            lambda contract_id: _make_contract(status="pending", vessel_id="vessel-abc"),
        )
        monkeypatch.setattr(
            contracts_api,
            "_get_current_eligibility",
            lambda contract: {
                "eligible": False,
                "reasons": ["Vessel is outside operational range"],
            },
        )

        rv = client.post(
            "/api/contracts/contract-001/accept",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
            json={"committedPowerKw": 25},
        )

        assert rv.status_code == 409
        assert "outside operational range" in rv.get_json()["error"]

    def test_resume_booking_context_returns_live_slots(self, client, monkeypatch):
        import api.contracts as contracts_api

        monkeypatch.setattr(
            contracts_api,
            "_get_owned_vessel_ids",
            lambda user_id: ["vessel-abc"],
        )
        monkeypatch.setattr(
            contracts_api.contract_service,
            "get_contract",
            lambda contract_id: {
                **_make_contract(status="pending", vessel_id="vessel-abc"),
                "acceptedAt": "2026-03-10T07:00:00+00:00",
                "committedPowerKw": 25,
            },
        )
        monkeypatch.setattr(
            contracts_api.booking_service,
            "get_station_availability",
            lambda station_id, start_time_raw, end_time_raw: {
                "stationId": "station-xyz",
                "startTime": "2026-03-10T08:00:00+00:00",
                "endTime": "2026-03-10T12:00:00+00:00",
                "chargers": [
                    {
                        "chargerId": "charger-1",
                        "chargerType": "Type 2 AC",
                        "available": True,
                    }
                ],
            },
        )
        monkeypatch.setattr(
            contracts_api.contract_service.drevent_repository,
            "get_event",
            lambda event_id: {
                "id": event_id,
                "stationId": "station-xyz",
            },
        )

        rv = client.get(
            "/api/contracts/contract-001/booking-context",
            headers=_jwt_headers(user_id="user-vo-001", user_type=1),
        )

        assert rv.status_code == 200
        payload = rv.get_json()
        assert payload["contract"]["id"] == "contract-001"
        assert payload["bookingContext"]["stationId"] == "station-xyz"
        assert payload["bookingContext"]["availableSlots"][0]["chargerId"] == "charger-1"

    def test_start_rejects_non_committed_event(self, client, monkeypatch):
        import api.drevents as drevents_api

        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()
        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Accepted"},
        )

        rv = client.post(
            "/api/drevents/dr-001/start",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 400
        assert "committed" in rv.get_json()["error"].lower()

    def test_start_uses_only_booked_active_contracts(self, client, monkeypatch):
        import api.drevents as drevents_api

        captured = {}
        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()

        class _FakeDynamoClient:
            def __init__(self, table_name, region_name):
                self.table_name = table_name
                self.region_name = region_name

            def scan_items(self):
                return [
                    {
                        **_make_contract(status="active", vessel_id="vessel-abc"),
                        "id": "contract-active-booked",
                        "bookingId": "booking-123",
                    },
                    {
                        **_make_contract(status="active", vessel_id="vessel-abc"),
                        "id": "contract-active-unbooked",
                        "bookingId": None,
                    },
                    {
                        **_make_contract(status="pending", vessel_id="vessel-abc"),
                        "id": "contract-pending-booked",
                        "bookingId": "booking-999",
                    },
                ]

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Committed"},
        )
        monkeypatch.setattr(
            drevents_api.drevent_service,
            "update_event",
            lambda event_id, update_data: {"id": event_id, **update_data},
        )
        monkeypatch.setattr(drevents_api, "DynamoClient", _FakeDynamoClient)
        monkeypatch.setattr(
            drevents_api,
            "_start_dispatch_loop_async",
            lambda event_id, valid_contracts, stop_signal: captured.update(
                {
                    "event_id": event_id,
                    "contracts": valid_contracts,
                    "stop_signal_set": stop_signal.is_set(),
                }
            ),
        )

        rv = client.post(
            "/api/drevents/dr-001/start",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 202
        assert captured["event_id"] == "dr-001"
        assert [contract["id"] for contract in captured["contracts"]] == [
            "contract-active-booked"
        ]
        assert captured["stop_signal_set"] is False
        assert rv.get_json()["status"] == "Active"

    def test_start_rejects_when_no_booked_active_contracts_exist(self, client, monkeypatch):
        import api.drevents as drevents_api

        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()

        class _FakeDynamoClient:
            def __init__(self, table_name, region_name):
                self.table_name = table_name
                self.region_name = region_name

            def scan_items(self):
                return [
                    {**_make_contract(status="pending", vessel_id="vessel-abc")},
                    {
                        **_make_contract(status="active", vessel_id="vessel-abc"),
                        "id": "contract-active-unbooked",
                        "bookingId": None,
                    },
                ]

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Committed"},
        )
        monkeypatch.setattr(drevents_api, "DynamoClient", _FakeDynamoClient)

        rv = client.post(
            "/api/drevents/dr-001/start",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 400
        assert "booked active contracts" in rv.get_json()["error"].lower()

    def test_start_rejects_duplicate_dispatch_for_same_event(self, client, monkeypatch):
        import api.drevents as drevents_api

        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()

        class _FakeDynamoClient:
            def __init__(self, table_name, region_name):
                self.table_name = table_name
                self.region_name = region_name

            def scan_items(self):
                return [
                    {
                        **_make_contract(status="active", vessel_id="vessel-abc"),
                        "id": "contract-active-booked",
                        "bookingId": "booking-123",
                    }
                ]

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Committed"},
        )
        monkeypatch.setattr(
            drevents_api.drevent_service,
            "update_event",
            lambda event_id, update_data: {"id": event_id, **update_data},
        )
        monkeypatch.setattr(drevents_api, "DynamoClient", _FakeDynamoClient)
        monkeypatch.setattr(
            drevents_api,
            "_start_dispatch_loop_async",
            lambda event_id, valid_contracts, stop_signal: None,
        )

        first_response = client.post(
            "/api/drevents/dr-001/start",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )
        second_response = client.post(
            "/api/drevents/dr-001/start",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert first_response.status_code == 202
        assert second_response.status_code == 409
        assert "already running" in second_response.get_json()["error"].lower()
        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()

    def test_end_rejects_non_active_event(self, client, monkeypatch):
        import api.drevents as drevents_api

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Committed"},
        )

        rv = client.post(
            "/api/drevents/dr-001/end",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 400
        assert "active" in rv.get_json()["error"].lower()

    def test_end_marks_event_completed_and_requests_dispatch_stop(
        self, client, monkeypatch
    ):
        import api.drevents as drevents_api

        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()

        updates = []
        stop_signal = drevents_api.Event()
        drevents_api._running_dispatch_event_ids.add("dr-001")
        drevents_api._dispatch_stop_signals["dr-001"] = stop_signal

        monkeypatch.setattr(
            drevents_api.drevent_service,
            "get_event",
            lambda event_id: {"id": event_id, "status": "Active"},
        )
        monkeypatch.setattr(
            drevents_api.drevent_service,
            "update_event",
            lambda event_id, update_data: updates.append((event_id, update_data))
            or {"id": event_id, **update_data},
        )

        rv = client.post(
            "/api/drevents/dr-001/end",
            headers=_jwt_headers(user_id="power-001", user_type=2),
        )

        assert rv.status_code == 200
        assert rv.get_json()["status"] == "Completed"
        assert rv.get_json()["dispatchStopped"] is True
        assert stop_signal.is_set() is True
        assert updates == [("dr-001", {"status": "Completed"})]
        drevents_api._running_dispatch_event_ids.clear()
        drevents_api._dispatch_stop_signals.clear()


# ---------------------------------------------------------------------------
# State transition guard tests (pure service logic)
# ---------------------------------------------------------------------------


class TestStateTransitionGuards:
    """Verify that invalid transitions are always rejected regardless of caller."""

    @pytest.mark.parametrize(
        "from_status", ["active", "completed", "cancelled", "failed"]
    )
    def test_cannot_accept_from_non_pending(self, from_status):
        repo = InMemoryContractRepo(
            [_make_contract(status=from_status, vessel_id="v1")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["v1"])

        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize(
        "from_status", ["active", "completed", "cancelled", "failed"]
    )
    def test_cannot_decline_from_non_pending(self, from_status):
        repo = InMemoryContractRepo(
            [_make_contract(status=from_status, vessel_id="v1")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.decline_contract("contract-001", caller_vessel_ids=["v1"])

        assert exc_info.value.status_code == 400

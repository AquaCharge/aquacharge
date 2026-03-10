"""
Tests for SCRUM-169: contract dispatch and VO accept/decline flow.
Uses in-memory stub repositories — no DynamoDB calls.
"""

import pytest
from flask import Flask
from api.contracts import contracts_bp
from services.contracts.service import ContractService, ContractServiceError
from models.contract import ContractStatus


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
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def _auth_headers():
    """Return a fake Bearer token header."""
    return {"Authorization": "Bearer fake-token"}


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
        return {"id": vessel_id, "userId": "user-001", "chargerType": "AC"}


class _StubDREventRepo:
    def get_event(self, event_id):
        return {
            "id": event_id,
            "stationId": "station-xyz",
            "startTime": "2026-03-10T08:00:00+00:00",
            "endTime": "2026-03-10T12:00:00+00:00",
        }


class TestAcceptContract:
    def test_accept_pending_contract_transitions_to_active(self):
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
            "contract-001", caller_vessel_ids=["vessel-abc"]
        )

        assert result["status"] == ContractStatus.ACTIVE.value

    def test_accept_rejects_when_vessel_not_owned(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="pending", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-other"])

        assert exc_info.value.status_code == 403

    def test_accept_rejects_non_pending_contract(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="active", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])

        assert exc_info.value.status_code == 400

    def test_accept_rejects_completed_contract(self):
        repo = InMemoryContractRepo(
            [_make_contract(status="completed", vessel_id="vessel-abc")]
        )
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("contract-001", caller_vessel_ids=["vessel-abc"])

        assert exc_info.value.status_code == 400

    def test_accept_missing_contract_returns_404(self):
        repo = InMemoryContractRepo([])
        service = ContractService(repository=repo)

        with pytest.raises(ContractServiceError) as exc_info:
            service.accept_contract("does-not-exist", caller_vessel_ids=["vessel-abc"])

        assert exc_info.value.status_code == 404


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

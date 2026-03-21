"""Tests for contract validation functions."""
import pytest
from unittest.mock import Mock, patch

from services.contracts.validation import (
    pre_event_contract_validation,
    post_event_contract_validation,
    MAX_FAILED_CONTRACTS,
)
from models.vessel import Vessel
from models.contract import Contract


class TestPreEventContractValidation:
    """Test pre_event_contract_validation function."""

    @patch('services.contracts.validation._contracts_client')
    def test_pre_event_validation_no_past_contracts(self, mock_client):
        """Test validation passes when vessel has no past contracts."""
        mock_client.query_gsi.return_value = []

        vessel = Mock(spec=Vessel)
        vessel.id = "vessel-123"

        result = pre_event_contract_validation(vessel)
        assert result is True
        mock_client.query_gsi.assert_called_once()

    @patch('services.contracts.validation._contracts_client')
    def test_pre_event_validation_with_completed_contracts(self, mock_client):
        """Test validation passes with completed contracts and good fulfillment."""
        mock_client.query_gsi.return_value = [
            {"id": "c1", "status": "completed"},
            {"id": "c2", "status": "completed"},
        ]

        vessel = Mock(spec=Vessel)
        vessel.id = "vessel-123"

        result = pre_event_contract_validation(vessel)
        assert result is True

    @patch('services.contracts.validation._contracts_client')
    def test_pre_event_validation_too_many_failed(self, mock_client):
        """Test validation fails when vessel has too many failed contracts."""
        mock_client.query_gsi.return_value = [
            {"id": "c1", "status": "failed"},
            {"id": "c2", "status": "failed"},
            {"id": "c3", "status": "failed"},
            {"id": "c4", "status": "completed"},
        ]

        vessel = Mock(spec=Vessel)
        vessel.id = "vessel-123"

        with pytest.raises(ValueError) as exc_info:
            pre_event_contract_validation(vessel)

        assert "failed contracts" in str(exc_info.value)
        assert str(MAX_FAILED_CONTRACTS) in str(exc_info.value)

    @patch('services.contracts.validation._contracts_client')
    def test_pre_event_validation_poor_fulfillment_rate(self, mock_client):
        """Test validation fails when fulfillment rate is too low."""
        # 2 failed, 3 completed = 66.7% fulfillment (below 75% limit, should fail)
        mock_client.query_gsi.return_value = [
            {"id": "c1", "status": "failed"},
            {"id": "c2", "status": "failed"},
            {"id": "c3", "status": "completed"},
            {"id": "c4", "status": "completed"},
            {"id": "c5", "status": "completed"},
        ]

        vessel = Mock(spec=Vessel)
        vessel.id = "vessel-123"

        with pytest.raises(ValueError) as exc_info:
            pre_event_contract_validation(vessel)

        assert "fulfillment rate" in str(exc_info.value)
        assert "75%" in str(exc_info.value)

    @patch('services.contracts.validation._contracts_client')
    def test_pre_event_validation_at_threshold(self, mock_client):
        """Test validation passes at the fulfillment threshold."""
        # 2 failed, 8 completed = 75% fulfillment (exactly at limit)
        mock_client.query_gsi.return_value = [
            {"id": "c1", "status": "failed"},
            {"id": "c2", "status": "failed"},
        ] + [{"id": f"c{i}", "status": "completed"} for i in range(3, 11)]

        vessel = Mock(spec=Vessel)
        vessel.id = "vessel-123"

        result = pre_event_contract_validation(vessel)
        assert result is True


class TestPostEventContractValidation:
    """Test post_event_contract_validation function."""

    @patch('services.contracts.validation._measurements_client')
    @patch('services.contracts.validation._contracts_client')
    def test_post_event_validation_sufficient_energy(self, mock_contracts_client, mock_measurements_client):
        """Test validation succeeds when energy delivery meets threshold."""
        # Setup: promised 100 kWh, delivered 95 kWh (meets 90% threshold)
        mock_measurements_client.query_gsi.return_value = [
            {"energyKwh": 50},
            {"energyKwh": 45},
        ]

        contract_obj = Mock(spec=Contract)
        contract_obj.id = "contract-123"
        contract_obj.vesselId = "vessel-123"
        contract_obj.drEventId = "event-123"
        contract_obj.energyAmount = 100

        result = post_event_contract_validation(contract_obj)

        assert result == "completed"
        mock_contracts_client.update_item.assert_called_once()
        call_args = mock_contracts_client.update_item.call_args
        assert call_args[1]['update_data']['status'] == "completed"

    @patch('services.contracts.validation._measurements_client')
    @patch('services.contracts.validation._contracts_client')
    def test_post_event_validation_insufficient_energy(self, mock_contracts_client, mock_measurements_client):
        """Test validation marks contract as FAILED when energy delivery is insufficient."""
        # Setup: promised 100 kWh, delivered 85 kWh (below 90% threshold)
        mock_measurements_client.query_gsi.return_value = [
            {"energyKwh": 50},
            {"energyKwh": 35},
        ]

        contract_obj = Mock(spec=Contract)
        contract_obj.id = "contract-123"
        contract_obj.vesselId = "vessel-123"
        contract_obj.drEventId = "event-123"
        contract_obj.energyAmount = 100

        result = post_event_contract_validation(contract_obj)

        assert result == "failed"
        mock_contracts_client.update_item.assert_called_once()
        call_args = mock_contracts_client.update_item.call_args
        assert call_args[1]['update_data']['status'] == "failed"

    @patch('services.contracts.validation._measurements_client')
    def test_post_event_validation_no_measurements(self, mock_measurements_client):
        """Test validation raises error when no measurements found."""
        mock_measurements_client.query_gsi.return_value = []

        contract_obj = Mock(spec=Contract)
        contract_obj.vesselId = "vessel-123"
        contract_obj.drEventId = "event-123"

        with pytest.raises(ValueError) as exc_info:
            post_event_contract_validation(contract_obj)

        assert "No measurements found" in str(exc_info.value)

    @patch('services.contracts.validation._measurements_client')
    @patch('services.contracts.validation._contracts_client')
    def test_post_event_validation_decimal_precision(self, mock_contracts_client, mock_measurements_client):
        """Test validation handles decimal precision correctly."""
        mock_measurements_client.query_gsi.return_value = [
            {"energyKwh": 89.99},
        ]

        contract_obj = Mock(spec=Contract)
        contract_obj.id = "contract-123"
        contract_obj.vesselId = "vessel-123"
        contract_obj.drEventId = "event-123"
        contract_obj.energyAmount = 100  # Threshold is 90 kWh

        result = post_event_contract_validation(contract_obj)

        # 89.99 < 90, so should be FAILED
        assert result == "failed"

    @patch('services.contracts.validation._measurements_client')
    @patch('services.contracts.validation._contracts_client')
    def test_post_event_validation_accepts_raw_contract_dict(
        self, mock_contracts_client, mock_measurements_client
    ):
        """Test validation accepts raw contract dictionaries from the dispatch loop."""
        mock_measurements_client.query_gsi.return_value = [
            {"energyKwh": 95, "drEventId": "event-123"},
        ]

        result = post_event_contract_validation(
            {
                "id": "contract-123",
                "vesselId": "vessel-123",
                "drEventId": "event-123",
                "vesselName": "Sea Breeze",
                "energyAmount": 100,
                "pricePerKwh": 0.2,
                "startTime": "2026-03-10T08:00:00+00:00",
                "endTime": "2026-03-10T12:00:00+00:00",
                "status": "active",
                "terms": "Standard terms",
                "createdAt": "2026-03-09T00:00:00+00:00",
                "createdBy": "pso-001",
            }
        )

        assert result == "completed"
        mock_contracts_client.update_item.assert_called_once()

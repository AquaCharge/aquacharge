"""Unit tests for monitoring.py"""

import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# _JsonFormatter
# ---------------------------------------------------------------------------

class TestJsonFormatter:
    def _make_formatter(self):
        from monitoring import _JsonFormatter
        return _JsonFormatter()

    def _make_record(self, msg="hello", **extra):
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg=msg, args=(), exc_info=None,
        )
        for k, v in extra.items():
            setattr(record, k, v)
        return record

    def test_basic_fields_present(self):
        fmt = self._make_formatter()
        output = json.loads(fmt.format(self._make_record("test msg")))
        assert output["level"] == "INFO"
        assert output["message"] == "test msg"
        assert "time" in output
        assert "logger" in output

    def test_extra_fields_included(self):
        fmt = self._make_formatter()
        record = self._make_record("msg", log_group="/my/group")
        output = json.loads(fmt.format(record))
        assert output["log_group"] == "/my/group"

    def test_non_serializable_extra_does_not_raise(self):
        """default=str should handle datetime/Decimal/etc. without raising."""
        import datetime
        fmt = self._make_formatter()
        record = self._make_record("msg", ts=datetime.datetime(2024, 1, 1))
        # Should not raise
        result = fmt.format(record)
        assert json.loads(result)  # valid JSON

    def test_exc_info_included(self):
        fmt = self._make_formatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test", level=logging.ERROR,
                pathname="", lineno=0, msg="err", args=(), exc_info=sys.exc_info(),
            )
        output = json.loads(fmt.format(record))
        assert "exc_info" in output
        assert "ValueError" in output["exc_info"]


# ---------------------------------------------------------------------------
# emit_metric
# ---------------------------------------------------------------------------

class TestEmitMetric:
    def test_noop_when_disabled(self):
        """emit_metric must not call boto3 when CLOUDWATCH_ENABLED is false."""
        import monitoring
        with patch.object(monitoring, "CLOUDWATCH_ENABLED", False):
            with patch.object(monitoring, "_get_metrics_client") as mock_client:
                monitoring.emit_metric("TestMetric", 1.0)
                mock_client.assert_not_called()

    def test_calls_put_metric_when_enabled(self):
        import monitoring
        mock_client = MagicMock()
        with patch.object(monitoring, "CLOUDWATCH_ENABLED", True):
            with patch.object(monitoring, "_get_metrics_client", return_value=mock_client):
                monitoring.emit_metric("RequestCount", 1, "Count", [{"Name": "Env", "Value": "test"}])
        mock_client.put_metric_data.assert_called_once()
        call_kwargs = mock_client.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == monitoring.METRICS_NAMESPACE
        assert call_kwargs["MetricData"][0]["MetricName"] == "RequestCount"

    def test_swallows_botocore_errors(self):
        """emit_metric should log a warning but not raise on AWS errors."""
        import monitoring
        from botocore.exceptions import ClientError
        mock_client = MagicMock()
        mock_client.put_metric_data.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "down"}}, "PutMetricData"
        )
        with patch.object(monitoring, "CLOUDWATCH_ENABLED", True):
            with patch.object(monitoring, "_get_metrics_client", return_value=mock_client):
                # Must not raise
                monitoring.emit_metric("X", 1)


# ---------------------------------------------------------------------------
# record_request_start / record_request_end
# ---------------------------------------------------------------------------

class TestRequestLifecycle:
    @pytest.fixture()
    def app(self):
        flask_app = Flask(__name__)
        flask_app.config["TESTING"] = True
        return flask_app

    def test_record_request_start_sets_monotonic_time(self, app):
        import monitoring
        with app.test_request_context("/"):
            from flask import g
            before = time.monotonic()
            monitoring.record_request_start(g)
            after = time.monotonic()
            assert before <= g.request_start <= after

    def test_record_request_end_emits_metrics(self, app):
        import monitoring
        mock_response = MagicMock()
        mock_response.status_code = 200

        with app.test_request_context("/"):
            from flask import g
            monitoring.record_request_start(g)

            with patch.object(monitoring, "CLOUDWATCH_ENABLED", True):
                with patch.object(monitoring, "_get_metrics_client") as mock_cw:
                    mock_client = MagicMock()
                    mock_cw.return_value = mock_client
                    monitoring.record_request_end(g, mock_response, "health", "GET")

            # Two metrics: RequestCount + ResponseLatency
            assert mock_client.put_metric_data.call_count == 2

    def test_record_request_end_emits_error_metric_on_4xx(self, app):
        import monitoring
        mock_response = MagicMock()
        mock_response.status_code = 404

        with app.test_request_context("/"):
            from flask import g
            monitoring.record_request_start(g)

            with patch.object(monitoring, "CLOUDWATCH_ENABLED", True):
                with patch.object(monitoring, "_get_metrics_client") as mock_cw:
                    mock_client = MagicMock()
                    mock_cw.return_value = mock_client
                    monitoring.record_request_end(g, mock_response, "not_found", "GET")

            # RequestCount + ResponseLatency + ErrorCount = 3
            assert mock_client.put_metric_data.call_count == 3

    def test_record_request_end_no_op_when_start_missing(self, app):
        """Should return early without raising if request_start was never set."""
        import monitoring
        mock_response = MagicMock()
        mock_response.status_code = 200

        with app.test_request_context("/"):
            from flask import g
            # Deliberately do NOT call record_request_start
            with patch.object(monitoring, "_get_metrics_client") as mock_cw:
                monitoring.record_request_end(g, mock_response, "health", "GET")
                mock_cw.assert_not_called()

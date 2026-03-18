"""
CloudWatch monitoring: structured logging and custom metrics.

Controlled by env vars:
  CLOUDWATCH_ENABLED=true       – emit logs/metrics to AWS (default: false)
  CLOUDWATCH_LOG_GROUP          – log group name (default: /aquacharge/backend)
  CLOUDWATCH_NAMESPACE          – custom metrics namespace (default: AquaCharge/Backend)
  AWS_REGION                    – AWS region (default: us-east-1)
  AWS_ENDPOINT_URL              – override endpoint, e.g. http://localstack:4566 for local dev
"""

import json
import logging
import os
import sys
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

CLOUDWATCH_ENABLED = os.environ.get("CLOUDWATCH_ENABLED", "false").lower() == "true"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.environ.get(
    "AWS_ENDPOINT_URL"
)  # None → real AWS; set for LocalStack
LOG_GROUP = os.environ.get("CLOUDWATCH_LOG_GROUP", "/aquacharge/backend")
METRICS_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "AquaCharge/Backend")


def _boto_client(service: str):
    """Create a boto3 client, routing to LocalStack when AWS_ENDPOINT_URL is set."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client(service, **kwargs)


logger = logging.getLogger("aquacharge")


_LOG_RECORD_BUILTINS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON, including any extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_BUILTINS:
                payload[key] = value
        return json.dumps(payload, default=str)


def setup_logging() -> logging.Logger:
    """
    Configure the root 'aquacharge' logger.

    Always attaches a stdout StreamHandler with JSON formatting.
    When CLOUDWATCH_ENABLED, also attaches a watchtower CloudWatch Logs handler.
    """
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(_JsonFormatter())
    logger.addHandler(stream_handler)

    if CLOUDWATCH_ENABLED:
        try:
            import watchtower  # noqa: PLC0415 – optional dependency

            cw_logs_client = _boto_client("logs")
            send_interval = (
                5 if AWS_ENDPOINT_URL else 60
            )  # flush faster against LocalStack
            cw_handler = watchtower.CloudWatchLogHandler(
                log_group_name=LOG_GROUP,
                log_stream_name="{strftime:%Y-%m-%d}",
                boto3_client=cw_logs_client,
                create_log_group=True,
                send_interval=send_interval,
            )
            cw_handler.setFormatter(_JsonFormatter())
            logger.addHandler(cw_handler)
            logger.info(
                "CloudWatch Logs handler attached", extra={"log_group": LOG_GROUP}
            )
        except ImportError:
            logger.warning("watchtower not installed – CloudWatch Logs disabled")
        except (BotoCoreError, ClientError) as exc:
            logger.warning("Could not attach CloudWatch Logs handler: %s", exc)

    return logger


# ---------------------------------------------------------------------------
# Custom metrics
# ---------------------------------------------------------------------------

_cw_metrics_client = None


def _get_metrics_client():
    global _cw_metrics_client
    if _cw_metrics_client is None:
        _cw_metrics_client = _boto_client("cloudwatch")
    return _cw_metrics_client


def emit_metric(
    name: str,
    value: float,
    unit: str = "Count",
    dimensions: list[dict] | None = None,
) -> None:
    """
    Put a single custom metric to CloudWatch.  No-op when CLOUDWATCH_ENABLED is false.

    Args:
        name:       Metric name, e.g. "RequestCount".
        value:      Numeric value.
        unit:       CloudWatch unit string (Count, Milliseconds, Bytes, …).
        dimensions: List of {"Name": str, "Value": str} dicts.
    """
    if not CLOUDWATCH_ENABLED:
        return

    metric_datum: dict = {"MetricName": name, "Value": value, "Unit": unit}
    if dimensions:
        metric_datum["Dimensions"] = dimensions

    try:
        _get_metrics_client().put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[metric_datum],
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Failed to emit metric %s: %s", name, exc)


# ---------------------------------------------------------------------------
# Flask integration helpers
# ---------------------------------------------------------------------------


def record_request_start(g) -> None:
    """Store request start time on Flask's g object."""
    g.request_start = time.monotonic()


def record_request_end(g, response, endpoint: str, method: str) -> None:
    """
    Emit RequestCount, ResponseLatency, and (when applicable) ErrorCount metrics.
    Also log the completed request at INFO level.
    """
    start_time = getattr(g, "request_start", None)
    if start_time is None:
        logger.debug("record_request_end called without request_start on g; skipping metrics")
        return

    elapsed_ms = (time.monotonic() - start_time) * 1000
    status_code = response.status_code

    dims = [
        {"Name": "Endpoint", "Value": endpoint or "unknown"},
        {"Name": "Method", "Value": method},
    ]

    emit_metric("RequestCount", 1, "Count", dims)
    emit_metric("ResponseLatency", round(elapsed_ms, 2), "Milliseconds", dims)

    if status_code >= 400:
        error_dims = dims + [{"Name": "StatusCode", "Value": str(status_code)}]
        emit_metric("ErrorCount", 1, "Count", error_dims)

    if status_code == 429:
        emit_metric("RateLimitHit", 1, "Count", dims)

    logger.info(
        "%s %s → %d (%.1f ms)",
        method,
        endpoint or "unknown",
        status_code,
        elapsed_ms,
    )

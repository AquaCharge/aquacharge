from threading import Event

from services.dr import dispatcher


def test_dispatch_interval_uses_configured_override(monkeypatch):
    monkeypatch.setattr(dispatcher.config, "DR_DISPATCH_INTERVAL_SECONDS", 10)

    assert dispatcher.get_dispatch_interval_seconds() == 10


def test_dispatch_interval_never_returns_less_than_one(monkeypatch):
    monkeypatch.setattr(dispatcher.config, "DR_DISPATCH_INTERVAL_SECONDS", 0)

    assert dispatcher.get_dispatch_interval_seconds() == 1


def test_dispatch_loop_stops_without_writing_measurements_when_stop_requested(
    monkeypatch,
):
    class _UnexpectedDynamoClient:
        def __init__(self, table_name, region_name):
            raise AssertionError("dispatch loop should not initialize table clients")

    monkeypatch.setattr(dispatcher, "DynamoClient", _UnexpectedDynamoClient)
    stop_signal = Event()
    stop_signal.set()

    dispatcher._dispatch_loop(
        "dr-001",
        valid_contracts=[],
        dynamo_client=None,
        stop_signal=stop_signal,
    )

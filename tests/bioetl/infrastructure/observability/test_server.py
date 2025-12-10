from bioetl.infrastructure.observability.server import start_metrics_server_once


def test_metrics_server_once():
    assert start_metrics_server_once(enabled=False, port=9100, address="127.0.0.1") is False

    started = start_metrics_server_once(enabled=True, port=9101, address="127.0.0.1")
    assert started is True

    started_again = start_metrics_server_once(enabled=True, port=9101, address="127.0.0.1")
    assert started_again is False

from __future__ import annotations

import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace
from typing import Any, Iterable
from unittest.mock import MagicMock

import pytest

from bioetl.domain.configs import ChemblSourceConfig, ProviderHttpConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.chembl.factories import create_chembl_client
from bioetl.infrastructure.errors import ApiUnexpectedStatusError


@contextmanager
def _run_server(sequence: Iterable[tuple[int, dict[str, Any]]]):
    calls: dict[str, int] = {"count": 0}
    sequence_list = list(sequence)

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            idx = min(calls["count"], len(sequence_list) - 1)
            status, payload = sequence_list[idx]
            calls["count"] += 1
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield SimpleNamespace(base_url=f"http://{host}:{port}", calls=calls)
    finally:
        server.shutdown()
        thread.join()


def _make_client(base_url: str, *, max_retries: int) -> Any:
    http_config = ProviderHttpConfig(
        base_url=base_url,
        timeout_sec=1.0,
        max_retries=max_retries,
        backoff_factor=0.05,
        backoff_max=0.05,
    )
    config = ChemblSourceConfig(http=http_config)
    logger = MagicMock(spec=LoggingPortABC)
    metrics = MagicMock(spec=MetricsPortABC)
    return create_chembl_client(config, logger=logger, metrics=metrics, http_config=http_config)


@pytest.mark.integration
def test_chembl_client_retries_and_recovers():
    """Client retries transient failures and returns payload on success."""

    with _run_server([(503, {"error": "retry"}), (200, {"ok": True})]) as server:
        client = _make_client(server.base_url, max_retries=2)

        result = client.fetch("activity")

        assert result == {"ok": True}
        assert server.calls["count"] == 2


@pytest.mark.integration
def test_chembl_client_escalates_after_exhausting_retries():
    """Client raises after exhausting retry budget."""

    with _run_server([(500, {"error": "fail"}), (500, {"error": "fail"})]) as server:
        client = _make_client(server.base_url, max_retries=1)

        with pytest.raises(ApiUnexpectedStatusError):
            client.fetch("activity")

        assert server.calls["count"] == 2

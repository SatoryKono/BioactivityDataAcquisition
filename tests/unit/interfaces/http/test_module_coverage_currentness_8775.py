"""HTTP-interface coverage regression vectors for #8775."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest

from bioetl.interfaces.http import _health_server_observability_routing as routing
from bioetl.interfaces.http import report_root_config


pytestmark = pytest.mark.unit


class _Writer:
    pass


class _Host:
    def __init__(self) -> None:
        self._forensic_endpoint_limiter = asyncio.Semaphore(1)
        self._run_ledger_port = None
        self._prometheus_base_url = "http://prometheus.test"
        self.sent: list[tuple[int, dict[str, object]]] = []

    @staticmethod
    def _read_required_param(query: dict[str, str], name: str) -> str:
        return query[name]

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        return query.get(name)

    async def _send_payload_response(
        self,
        _writer: asyncio.StreamWriter,
        status: int,
        payload: dict[str, object],
    ) -> None:
        self.sent.append((status, payload))


@pytest.mark.asyncio
async def test_processed_records_backend_failure_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable(**_kwargs: object) -> object:
        raise RuntimeError("backend down")

    monkeypatch.setattr(routing, "run_bounded_forensic_operation", unavailable)
    host = _Host()

    await routing.handle_processed_records_table(
        host,
        cast("asyncio.StreamWriter", _Writer()),
        {"pipeline": "chembl_activity", "run_id": "run-1"},
    )

    assert host.sent[0][0] == 503
    assert host.sent[0][1]["reason"] == "backend_unavailable"


def test_runtime_source_id_value_delegates_to_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        report_root_config,
        "runtime_source_identity_resolution",
        lambda: SimpleNamespace(value="a" * 64),
    )

    assert report_root_config.runtime_source_id_value() == "a" * 64

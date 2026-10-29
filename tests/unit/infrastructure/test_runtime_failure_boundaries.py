"""Fail-closed IO, payload, redirect and cleanup boundaries from CI regressions."""

import io
import contextlib
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.request import Request
from urllib.error import HTTPError
from http.client import HTTPMessage

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.silver import support
from bioetl.infrastructure.storage.silver.schema_drift_operations import (
    _diff_schema_types,
)
from bioetl.infrastructure.storage.gold.io_delta_mixins import _GoldWriterScd2MergeMixin
from bioetl.infrastructure.observability import observability_backend_probes as probes

pytestmark = pytest.mark.unit


def test_reader_tolerates_closed_pipe_without_retaining_data():
    stream = io.BytesIO(b"unreadable")
    stream.close()
    reader = support._BoundedStreamReader(stream)
    reader.run()
    assert reader.get_decoded() == ""


def test_expired_subprocess_deadline_never_waits_again(monkeypatch):
    ticks = iter([0.0, 2.0])
    monkeypatch.setattr(support.time, "monotonic", lambda: next(ticks))
    process = SimpleNamespace(args=["child"], wait=MagicMock())
    with pytest.raises(subprocess.TimeoutExpired):
        support._wait_for_plain_delta_subprocess(
            process, timeout_seconds=1, cancel_event=None
        )
    process.wait.assert_not_called()


def test_expired_join_budget_does_not_block_on_reader(monkeypatch):
    ticks = iter([0.0, 0.0])
    monkeypatch.setattr(support.time, "monotonic", lambda: next(ticks, 2.0))
    reader = MagicMock()
    support._join_bounded_readers((reader,), timeout_seconds=1)
    reader.join.assert_not_called()


def test_failed_reader_start_reaps_child_and_closes_both_pipes(monkeypatch):
    process = SimpleNamespace(
        stdout=io.BytesIO(),
        stderr=io.BytesIO(),
        returncode=None,
        kill=MagicMock(),
        wait=MagicMock(),
    )
    monkeypatch.setattr(support.subprocess, "Popen", lambda *a, **k: process)
    reader = MagicMock()
    reader.start.side_effect = RuntimeError("thread unavailable")
    monkeypatch.setattr(support, "_BoundedStreamReader", lambda *a: reader)
    with pytest.raises(RuntimeError, match="thread unavailable"):
        support._execute_bounded_subprocess(
            ["child"], timeout_seconds=1, cancel_event=None
        )
    process.kill.assert_called_once()
    assert process.stdout.closed and process.stderr.closed


def test_scd2_snapshot_rejects_missing_business_keys():
    with pytest.raises(ValueError, match="at least one business key"):
        _GoldWriterScd2MergeMixin._build_current_snapshot_filter(
            business_keys=[], current_flag_col="current", records=[{"id": 1}]
        )


@pytest.mark.asyncio
async def test_empty_scd2_batch_performs_no_delta_io():
    delta = MagicMock()
    await _GoldWriterScd2MergeMixin._merge_scd2(
        SimpleNamespace(), delta, [], "id", MagicMock(), MagicMock()
    )
    delta.merge.assert_not_called()


@pytest.mark.asyncio
async def test_scd2_reserved_control_column_is_rejected_before_io():
    delta = MagicMock()
    with pytest.raises(ValueError, match="Reserved SCD2 source field"):
        await _GoldWriterScd2MergeMixin._merge_scd2(
            SimpleNamespace(),
            delta,
            [{"id": 1, "__bioetl_scd2_expire": True}],
            "id",
            MagicMock(),
            MagicMock(),
        )
    delta.merge.assert_not_called()


def test_empty_batch_or_missing_schema_has_no_type_drift():
    assert _diff_schema_types(None, [{"id": 1}]) == ()
    assert _diff_schema_types(pa.schema([("id", pa.int64())]), []) == ()


def test_observability_redirects_cannot_escape_http():
    opener = MagicMock(side_effect=AssertionError("Non-HTTP probes must never open IO"))
    assert not probes.probe_observability_backend_required_paths(
        "file:///private", required_probe_paths=("/ready",), urlopen_fn=opener
    )
    opener.assert_not_called()
    handler = probes._HttpHttpsRedirectHandler()
    request = Request("https://example.test/start")
    with pytest.raises(HTTPError, match="not allowed"):
        handler.redirect_request(
            request, None, 302, "Found", HTTPMessage(), "file:///private"
        )
    redirected = handler.redirect_request(
        request, None, 302, "Found", HTTPMessage(), "https://example.test/ready"
    )
    assert redirected.full_url == "https://example.test/ready"


def test_probe_forwards_timeout_to_http_opener(monkeypatch):
    opener = MagicMock()
    monkeypatch.setattr(probes, "build_opener", lambda *_: opener)
    result = probes._open_observability_probe(
        "https://example.test/ready", timeout=0.25
    )
    assert result is opener.open.return_value
    opener.open.assert_called_once_with("https://example.test/ready", timeout=0.25)


def test_error_status_is_not_a_successful_readiness_probe():
    response = MagicMock()
    response.__enter__.return_value.status = 503
    assert not probes.probe_observability_backend(
        "https://example.test/ready", urlopen_fn=lambda *a, **k: response
    )


@pytest.mark.asyncio
async def test_pubmed_oversized_stream_fails_and_closes_response(monkeypatch):
    from bioetl.infrastructure.adapters.pubmed import _fetch

    monkeypatch.setattr(_fetch, "_MAX_XML_BYTES", 4)

    async def chunks():
        yield b"12345"

    response = SimpleNamespace(aiter_bytes=chunks, aclose=AsyncMock())
    host = SimpleNamespace(
        provider_name="pubmed",
        _error_handler=SimpleNamespace(handle_error=lambda **kwargs: kwargs["error"]),
        _build_fetch_params=lambda ids: {"id": ",".join(ids)},
        _adapter_metrics=SimpleNamespace(
            measure_request=lambda _: contextlib.nullcontext()
        ),
        http_client=SimpleNamespace(
            timeout=1,
            read_timeout_multiplier=1,
            stream=AsyncMock(return_value=response),
        ),
    )
    with pytest.raises(ValueError, match="exceeds limit"):
        await _fetch.PubMedFetchMixin._fetch_batch(host, ["1"])
    response.aclose.assert_awaited_once()

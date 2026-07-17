"""Tests for the fail-closed read-only observability stack launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qs, urlparse

import pytest

pytestmark = pytest.mark.unit


def _load_subject() -> ModuleType:
    path = Path("scripts/ops/observability/start_read_only_audit_stack.py")
    spec = importlib.util.spec_from_file_location("start_read_only_audit_stack", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def test_require_absolute_directory_is_fail_closed(tmp_path: Path) -> None:
    subject = _load_subject()

    assert (
        subject.require_absolute_directory(str(tmp_path), option_name="--data-root")
        == tmp_path.resolve()
    )
    with pytest.raises(ValueError, match="must be an absolute path"):
        subject.require_absolute_directory("relative", option_name="--data-root")
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="must identify a directory"):
        subject.require_absolute_directory(str(file_path), option_name="--data-root")


def test_promtail_sentinel_write_is_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _load_subject()
    observed: dict[str, Path] = {}
    real_replace = subject.os.replace

    def observe_replace(source: Path, target: Path) -> None:
        observed.update(source=source, target=target)
        assert source.suffix == ".tmp"
        assert source.is_file()
        assert not target.exists()
        real_replace(source, target)

    monkeypatch.setattr(subject.os, "replace", observe_replace)

    marker = subject.write_promtail_audit_sentinel(
        tmp_path,
        sentinel_id="atomic",
    )

    target = tmp_path / "bioetl-promtail-audit-sentinel-atomic.log"
    assert observed["target"] == target
    assert marker in target.read_text(encoding="utf-8")
    assert list(tmp_path.glob("*.tmp")) == []


def test_promtail_query_range_is_anchored_to_sentinel_write_time() -> None:
    subject = _load_subject()
    requested_urls: list[str] = []
    sentinel_written_ns = 400_000_000_000

    def fake_open(url: str, **_kwargs: object) -> _Response:
        requested_urls.append(url)
        if url == subject.PROMTAIL_READY_URL:
            return _Response(b"Ready\n")
        return _Response({"status": "success", "data": {"result": []}})

    result = subject.probe_promtail_audit_delivery(
        marker=f"{subject.PROMTAIL_SENTINEL_PREFIX}window",
        sentinel_written_ns=sentinel_written_ns,
        opener=fake_open,
        wall_time_ns=lambda: 900_000_000_000,
    )

    query = parse_qs(urlparse(requested_urls[-1]).query)
    assert result.state is subject.PromtailAuditState.PENDING
    assert int(query["start"][0]) == (
        sentinel_written_ns - subject.PROMTAIL_SENTINEL_CLOCK_SKEW_NS
    )
    assert int(query["end"][0]) == 900_000_000_000


def test_bounded_request_timeout_uses_only_remaining_budget() -> None:
    subject = _load_subject()

    assert subject._bounded_request_timeout(
        deadline=2.0,
        monotonic=lambda: 1.75,
    ) == pytest.approx(0.25)
    with pytest.raises(TimeoutError, match="budget exhausted"):
        subject._bounded_request_timeout(
            deadline=2.0,
            monotonic=lambda: 2.0,
        )


def test_promtail_probe_reports_exhausted_readiness_budget_as_timeout() -> None:
    subject = _load_subject()

    result = subject.probe_promtail_audit_delivery(
        marker=f"{subject.PROMTAIL_SENTINEL_PREFIX}readiness-timeout",
        sentinel_written_ns=0,
        deadline=1.0,
        monotonic=lambda: 1.0,
    )

    assert result.state is subject.PromtailAuditState.TIMEOUT
    assert "readiness request timed out" in result.detail
    assert "budget exhausted" in result.detail


def test_promtail_probe_reports_exhausted_loki_budget_as_timeout() -> None:
    subject = _load_subject()
    ticks = iter((0.5, 1.0))

    result = subject.probe_promtail_audit_delivery(
        marker=f"{subject.PROMTAIL_SENTINEL_PREFIX}loki-timeout",
        sentinel_written_ns=0,
        opener=lambda *_args, **_kwargs: _Response(b"Ready\n"),
        deadline=1.0,
        monotonic=lambda: next(ticks),
    )

    assert result.state is subject.PromtailAuditState.TIMEOUT
    assert "Loki sentinel query timed out" in result.detail
    assert "budget exhausted" in result.detail


def test_start_and_verify_routes_grafana_backend_to_requested_root(
    tmp_path: Path,
) -> None:
    subject = _load_subject()
    data_root = tmp_path / "data"
    log_root = tmp_path / "logs"
    probe_log_root = tmp_path / "probe-logs"
    data_root.mkdir()
    log_root.mkdir()
    captured: dict[str, object] = {}

    def fake_run(command: tuple[str, ...], **kwargs: object) -> object:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return object()

    def fake_open(url: str, **_kwargs: object) -> _Response:
        if url == subject.READY_URL:
            return _Response({"data_root": str(data_root.resolve())})
        if url == subject.CATALOG_URL:
            return _Response({"items": []})
        if url == subject.PROMTAIL_READY_URL:
            return _Response(b"Ready\n")
        assert url.startswith(subject.LOKI_QUERY_RANGE_URL)
        return _Response(
            {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "values": [
                                [
                                    "1700000000000000000",
                                    f"{subject.PROMTAIL_SENTINEL_PREFIX}test-success",
                                ]
                            ]
                        }
                    ]
                },
            }
        )

    result = subject.start_and_verify_audit_stack(
        data_root=data_root.resolve(),
        log_root=log_root.resolve(),
        timeout_seconds=5.0,
        run=fake_run,
        opener=fake_open,
        sentinel_id="test-success",
        wall_time_ns=lambda: 1_700_000_000_000_000_000,
        probe_log_root=probe_log_root,
    )

    assert result.state is subject.AuditBackendState.VALID_EMPTY
    assert result.item_count == 0
    command = captured["command"]
    assert isinstance(command, tuple)
    assert str(subject.AUDIT_COMPOSE) in command
    assert command[-7:] == (
        "prometheus",
        "pushgateway",
        "quarantine-explorer-audit",
        "loki",
        "promtail-audit",
        "grafana",
        "renderer",
    )
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    environment = kwargs["env"]
    assert isinstance(environment, dict)
    assert environment["BIOETL_AUDIT_DATA_ROOT"] == str(data_root.resolve())
    assert environment["BIOETL_AUDIT_LOG_ROOT"] == str(log_root.resolve())
    assert environment["BIOETL_AUDIT_PROBE_LOG_ROOT"] == str(probe_log_root.resolve())
    assert (
        probe_log_root / "bioetl-promtail-audit-sentinel-test-success.log"
    ).is_file()
    assert list(log_root.iterdir()) == []


def test_start_and_verify_rejects_backend_serving_wrong_root(tmp_path: Path) -> None:
    subject = _load_subject()
    ticks = iter((0.0, 0.1, 0.2))

    with pytest.raises(RuntimeError, match="backend served data_root"):
        subject.start_and_verify_audit_stack(
            data_root=tmp_path.resolve(),
            log_root=tmp_path.resolve(),
            timeout_seconds=1.0,
            run=lambda *_args, **_kwargs: object(),
            opener=lambda *_args, **_kwargs: _Response({"data_root": "/wrong"}),
            monotonic=lambda: next(ticks),
            sleep=lambda _seconds: None,
            probe_log_root=tmp_path / "probe-logs",
        )


def test_probe_classifies_backend_down(tmp_path: Path) -> None:
    subject = _load_subject()

    def unavailable(*_args: object, **_kwargs: object) -> _Response:
        raise OSError("connection refused")

    result = subject.probe_audit_backend(
        expected_data_root=tmp_path.resolve(),
        opener=unavailable,
    )

    assert result.state is subject.AuditBackendState.DOWN
    assert "connection refused" in result.detail


def test_probe_classifies_backend_timeout(tmp_path: Path) -> None:
    subject = _load_subject()

    def timed_out(*_args: object, **_kwargs: object) -> _Response:
        raise TimeoutError("deadline exceeded")

    result = subject.probe_audit_backend(
        expected_data_root=tmp_path.resolve(),
        opener=timed_out,
    )

    assert result.state is subject.AuditBackendState.TIMEOUT
    assert "deadline exceeded" in result.detail


def test_probe_classifies_backend_wrong_root(tmp_path: Path) -> None:
    subject = _load_subject()
    result = subject.probe_audit_backend(
        expected_data_root=tmp_path.resolve(),
        opener=lambda *_args, **_kwargs: _Response({"data_root": "/wrong"}),
    )

    assert result.state is subject.AuditBackendState.WRONG_ROOT
    assert result.data_root == "/wrong"


def test_probe_classifies_valid_empty_backend(tmp_path: Path) -> None:
    subject = _load_subject()

    def fake_open(url: str, **_kwargs: object) -> _Response:
        if url == subject.READY_URL:
            return _Response({"data_root": str(tmp_path.resolve())})
        assert url == subject.CATALOG_URL
        return _Response({"items": []})

    result = subject.probe_audit_backend(
        expected_data_root=tmp_path.resolve(),
        opener=fake_open,
    )

    assert result.state is subject.AuditBackendState.VALID_EMPTY
    assert result.item_count == 0


def test_probe_classifies_populated_backend(tmp_path: Path) -> None:
    subject = _load_subject()

    def fake_open(url: str, **_kwargs: object) -> _Response:
        if url == subject.READY_URL:
            return _Response({"data_root": str(tmp_path.resolve())})
        assert url == subject.CATALOG_URL
        return _Response({"items": ["chembl_activity", "chembl_assay"]})

    result = subject.probe_audit_backend(
        expected_data_root=tmp_path.resolve(),
        opener=fake_open,
    )

    assert result.state is subject.AuditBackendState.POPULATED
    assert result.item_count == 2

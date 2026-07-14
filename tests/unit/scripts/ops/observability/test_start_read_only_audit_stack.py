"""Tests for the fail-closed read-only observability stack launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

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
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
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


def test_start_and_verify_routes_grafana_backend_to_requested_root(
    tmp_path: Path,
) -> None:
    subject = _load_subject()
    data_root = tmp_path / "data"
    log_root = tmp_path / "logs"
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
        assert url == subject.CATALOG_URL
        return _Response({"items": []})

    result = subject.start_and_verify_audit_stack(
        data_root=data_root.resolve(),
        log_root=log_root.resolve(),
        timeout_seconds=5.0,
        run=fake_run,
        opener=fake_open,
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


def test_start_and_verify_rejects_backend_serving_wrong_root(tmp_path: Path) -> None:
    subject = _load_subject()
    ticks = iter((0.0, 0.1, 1.1, 1.2))

    with pytest.raises(RuntimeError, match="backend served data_root"):
        subject.start_and_verify_audit_stack(
            data_root=tmp_path.resolve(),
            log_root=tmp_path.resolve(),
            timeout_seconds=1.0,
            run=lambda *_args, **_kwargs: object(),
            opener=lambda *_args, **_kwargs: _Response({"data_root": "/wrong"}),
            monotonic=lambda: next(ticks),
            sleep=lambda _seconds: None,
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

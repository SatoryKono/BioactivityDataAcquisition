"""Runtime bind-owner discovery and explicit identity precedence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ops.runtime.docker import runtime_manager

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "uid,gid,expected_uid,expected_gid",
    [
        (1000, 1000, "1000", "1000"),
        (1000, 0, "1000", None),
        (0, 0, None, None),
    ],
)
def test_runtime_uses_nonroot_report_writer_identity(
    monkeypatch, tmp_path, uid, gid, expected_uid, expected_gid
):
    environment = {}
    monkeypatch.setattr(
        runtime_manager, "os", SimpleNamespace(name="posix", environ=environment)
    )
    monkeypatch.setattr(runtime_manager, "_load_contract", lambda _: {})
    monkeypatch.setattr(
        runtime_manager.runtime_preflight,
        "dashboard_source_environment",
        lambda *_: {
            "BIOETL_DASHBOARD_REPORT_ROOT": str(tmp_path / "reports"),
            "BIOETL_DASHBOARD_DATA_ROOT": str(tmp_path / "data"),
        },
    )
    monkeypatch.setattr(Path, "stat", lambda _: SimpleNamespace(st_uid=uid, st_gid=gid))
    with runtime_manager._dashboard_runtime_environment(
        tmp_path / "contract"
    ) as values:
        assert values.get("BIOETL_RUNTIME_UID") == expected_uid
        assert values.get("BIOETL_RUNTIME_GID") == expected_gid
    assert environment == {}


def test_dashboard_runtime_environment_skips_missing_bind_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing host bind dirs must not block ownership-optional dispatch."""
    environment: dict[str, str] = {}
    monkeypatch.setattr(
        runtime_manager, "os", SimpleNamespace(name="posix", environ=environment)
    )
    monkeypatch.setattr(runtime_manager, "_load_contract", lambda _: {})
    missing_reports = tmp_path / "missing-reports"
    missing_data = tmp_path / "missing-data"
    monkeypatch.setattr(
        runtime_manager.runtime_preflight,
        "dashboard_source_environment",
        lambda *_: {
            "BIOETL_DASHBOARD_REPORT_ROOT": str(missing_reports),
            "BIOETL_DASHBOARD_DATA_ROOT": str(missing_data),
            "BIOETL_RUNTIME_SOURCE_ID": "a" * 64,
        },
    )
    with runtime_manager._dashboard_runtime_environment(
        tmp_path / "contract"
    ) as values:
        assert "BIOETL_RUNTIME_UID" not in values
        assert "BIOETL_RUNTIME_GID" not in values
        assert values["BIOETL_RUNTIME_SOURCE_ID"] == "a" * 64
    assert environment == {}


def test_dashboard_runtime_environment_skips_owner_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Divergent reports/data owners must not publish BIOETL_RUNTIME_UID/GID."""
    environment: dict[str, str] = {}
    reports_path = tmp_path / "reports"
    data_path = tmp_path / "data"
    reports_path.mkdir()
    data_path.mkdir()
    monkeypatch.setattr(
        runtime_manager, "os", SimpleNamespace(name="posix", environ=environment)
    )
    monkeypatch.setattr(runtime_manager, "_load_contract", lambda _: {})
    monkeypatch.setattr(
        runtime_manager.runtime_preflight,
        "dashboard_source_environment",
        lambda *_: {
            "BIOETL_DASHBOARD_REPORT_ROOT": str(reports_path),
            "BIOETL_DASHBOARD_DATA_ROOT": str(data_path),
        },
    )

    def _stat_for_path(self: Path) -> SimpleNamespace:
        if self == reports_path:
            return SimpleNamespace(st_uid=1000, st_gid=1000)
        if self == data_path:
            return SimpleNamespace(st_uid=1001, st_gid=1001)
        raise FileNotFoundError(self)

    monkeypatch.setattr(Path, "stat", _stat_for_path)
    with runtime_manager._dashboard_runtime_environment(
        tmp_path / "contract"
    ) as values:
        assert "BIOETL_RUNTIME_UID" not in values
        assert "BIOETL_RUNTIME_GID" not in values
    assert environment == {}


@pytest.mark.parametrize(
    ("explicit", "detected"),
    [
        ({"BIOETL_RUNTIME_UID": "2000", "BIOETL_RUNTIME_GID": "2000"}, {}),
        ({"BIOETL_RUNTIME_UID": "2000"}, {"BIOETL_RUNTIME_GID": "1000"}),
        ({"BIOETL_RUNTIME_GID": "2000"}, {"BIOETL_RUNTIME_UID": "1000"}),
    ],
)
def test_dashboard_runtime_environment_preserves_explicit_runtime_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    explicit: dict[str, str],
    detected: dict[str, str],
) -> None:
    """Keep explicit fields, infer only unset ones, and restore environment."""
    environment = dict(explicit)
    reports_path = tmp_path / "reports"
    data_path = tmp_path / "data"
    reports_path.mkdir()
    data_path.mkdir()
    monkeypatch.setattr(
        runtime_manager, "os", SimpleNamespace(name="posix", environ=environment)
    )
    monkeypatch.setattr(runtime_manager, "_load_contract", lambda _: {})
    monkeypatch.setattr(
        runtime_manager.runtime_preflight,
        "dashboard_source_environment",
        lambda *_: {
            "BIOETL_DASHBOARD_REPORT_ROOT": str(reports_path),
            "BIOETL_DASHBOARD_DATA_ROOT": str(data_path),
        },
    )
    monkeypatch.setattr(
        Path, "stat", lambda _: SimpleNamespace(st_uid=1000, st_gid=1000)
    )
    with runtime_manager._dashboard_runtime_environment(
        tmp_path / "contract"
    ) as values:
        for key in explicit:
            assert key not in values
        for key, value in detected.items():
            assert values[key] == value
        for key, value in (explicit | detected).items():
            assert environment[key] == value
    assert environment == explicit

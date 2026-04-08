"""Unit-style no-API checks for provider drift helper diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.contract import _provider_contract_drift as drift

pytestmark = pytest.mark.no_api


def _write_snapshot(tmp_path: Path, *, payload: dict[str, object]) -> None:
    snapshot_path = tmp_path / "demo" / "v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_mismatch_diagnostics_include_breaking_severity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_snapshot(
        tmp_path,
        payload={
            "provider": "demo",
            "version": 1,
            "probes": {
                "probe": {
                    "paths": {
                        "status": "str",
                    }
                }
            },
        },
    )
    monkeypatch.setattr(drift, "CONTRACT_SNAPSHOTS_DIR", tmp_path)

    with pytest.raises(pytest.fail.Exception) as exc_info:
        drift.assert_provider_probe_matches_snapshot(
            "demo",
            "probe",
            {"status": 1},
        )

    message = str(exc_info.value)
    assert "severity=breaking" in message
    assert "paths_checked=1" in message
    assert "mismatched_paths=1" in message
    assert "status: expected 'str', got 'int'" in message


def test_path_resolution_diagnostics_include_breaking_severity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_snapshot(
        tmp_path,
        payload={
            "provider": "demo",
            "version": 1,
            "probes": {
                "probe": {
                    "paths": {
                        "message.items": "list",
                    }
                }
            },
        },
    )
    monkeypatch.setattr(drift, "CONTRACT_SNAPSHOTS_DIR", tmp_path)

    with pytest.raises(pytest.fail.Exception) as exc_info:
        drift.assert_provider_probe_matches_snapshot(
            "demo",
            "probe",
            {"message": {}},
        )

    message = str(exc_info.value)
    assert "provider contract snapshot path could not be resolved" in message
    assert "severity=breaking" in message
    assert "path='message.items'" in message
    assert "missing key 'items'" in message


def test_compare_provider_probe_to_snapshot_classifies_nullable_drift_as_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_snapshot(
        tmp_path,
        payload={
            "provider": "demo",
            "version": 1,
            "probes": {
                "probe": {
                    "paths": {
                        "message.title": "str",
                    }
                }
            },
        },
    )
    monkeypatch.setattr(drift, "CONTRACT_SNAPSHOTS_DIR", tmp_path)

    report = drift.compare_provider_probe_to_snapshot(
        "demo",
        "probe",
        {"message": {"title": None}},
    )

    assert report["status"] == "drift"
    assert report["severity"] == "warning"
    assert report["difference_count"] == 1
    difference = report["differences"][0]
    assert difference["kind"] == "type_changed"
    assert difference["expected_type"] == "str"
    assert difference["actual_type"] == "null"
    assert difference["severity"] == "warning"


def test_compare_provider_probe_to_snapshot_returns_benign_for_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_snapshot(
        tmp_path,
        payload={
            "provider": "demo",
            "version": 1,
            "probes": {
                "probe": {
                    "paths": {
                        "status": "str",
                    }
                }
            },
        },
    )
    monkeypatch.setattr(drift, "CONTRACT_SNAPSHOTS_DIR", tmp_path)

    report = drift.compare_provider_probe_to_snapshot(
        "demo",
        "probe",
        {"status": "ok"},
    )

    assert report["status"] == "match"
    assert report["severity"] == "benign"
    assert report["difference_count"] == 0

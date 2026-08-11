from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts.engineering.qa import refresh_test_governance_baseline as refresh

pytestmark = pytest.mark.unit


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sample_payload() -> dict[str, Any]:
    return {
        "report": {
            "duplicate_test_name_inventory_summary": {"count": 0},
            "duplicate_test_name_inventory": [],
            "fixture_asset_duplication": {"summary": {"duplicate_groups": 0}},
        }
    }


def test_check_json_artifact_accepts_canonical_match(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    payload: dict[str, object] = {"summary": {"count": 1}}
    _write_json(artifact, payload)

    assert refresh._check_json_artifact(artifact, payload) is True


@pytest.mark.parametrize("state", ["missing", "mismatch"])
def test_check_json_artifact_rejects_missing_or_mismatched_content(
    tmp_path: Path,
    state: str,
) -> None:
    artifact = tmp_path / "artifact.json"
    if state == "mismatch":
        _write_json(artifact, {"summary": {"count": 0}})

    assert refresh._check_json_artifact(artifact, {"summary": {"count": 1}}) is False


def test_main_check_mode_returns_nonzero_on_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "test-governance-current.json"
    fixture = tmp_path / "test-fixture-asset-duplication.json"
    _write_json(output, {"stale": True})
    _write_json(fixture, {"stale": True})

    payload = _sample_payload()
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_test_governance_baseline.py",
            "--check",
            "--output",
            str(output),
            "--fixture-duplication",
            str(fixture),
        ],
    )
    with (
        patch.object(refresh, "collect_test_governance_report", return_value=payload),
        patch.object(refresh, "DEFAULT_CONFIG", tmp_path / "missing-config.yaml"),
    ):
        assert refresh.main() == 1


def test_main_check_mode_returns_zero_when_artifacts_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _sample_payload()
    output = tmp_path / "test-governance-current.json"
    fixture = tmp_path / "test-fixture-asset-duplication.json"
    _write_json(output, payload)
    _write_json(fixture, payload["report"]["fixture_asset_duplication"])

    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_test_governance_baseline.py",
            "--check",
            "--output",
            str(output),
            "--fixture-duplication",
            str(fixture),
        ],
    )
    with (
        patch.object(refresh, "collect_test_governance_report", return_value=payload),
        patch.object(refresh, "DEFAULT_CONFIG", tmp_path / "missing-config.yaml"),
    ):
        assert refresh.main() == 0


def test_main_check_mode_rejects_stale_optional_duplicate_name_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _sample_payload()
    output = tmp_path / "test-governance-current.json"
    fixture = tmp_path / "test-fixture-asset-duplication.json"
    duplicate_names = tmp_path / "duplicate-test-name-inventory.json"
    _write_json(output, payload)
    _write_json(fixture, payload["report"]["fixture_asset_duplication"])
    _write_json(duplicate_names, {"stale": True})

    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_test_governance_baseline.py",
            "--check",
            "--output",
            str(output),
            "--fixture-duplication",
            str(fixture),
            "--duplicate-name-inventory",
            str(duplicate_names),
        ],
    )
    with (
        patch.object(refresh, "collect_test_governance_report", return_value=payload),
        patch.object(refresh, "DEFAULT_CONFIG", tmp_path / "missing-config.yaml"),
    ):
        assert refresh.main() == 1


def test_main_write_mode_refreshes_all_requested_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _sample_payload()
    output = tmp_path / "test-governance-current.json"
    fixture = tmp_path / "test-fixture-asset-duplication.json"
    duplicate_names = tmp_path / "duplicate-test-name-inventory.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_test_governance_baseline.py",
            "--output",
            str(output),
            "--fixture-duplication",
            str(fixture),
            "--duplicate-name-inventory",
            str(duplicate_names),
        ],
    )
    with (
        patch.object(refresh, "collect_test_governance_report", return_value=payload),
        patch.object(refresh, "DEFAULT_CONFIG", tmp_path / "missing-config.yaml"),
    ):
        assert refresh.main() == 0

    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert (
        json.loads(fixture.read_text(encoding="utf-8"))
        == payload["report"]["fixture_asset_duplication"]
    )
    assert json.loads(duplicate_names.read_text(encoding="utf-8")) == {
        "summary": payload["report"]["duplicate_test_name_inventory_summary"],
        "inventory": payload["report"]["duplicate_test_name_inventory"],
    }

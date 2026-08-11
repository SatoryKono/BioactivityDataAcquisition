from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import refresh_test_governance_baseline as refresh

pytestmark = pytest.mark.unit


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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

"""Tests for file-backed artifact comparison semantics."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.infrastructure.control_plane import FileArtifactByteComparisonAdapter


def _ref(path: Path) -> dict[str, object]:
    return {"artifact_path": str(path)}


def _metadata_ref(path: Path) -> dict[str, object]:
    return {"metadata_path": str(path)}


def test_compare_artifacts_reports_raw_byte_equivalent_files(tmp_path: Path) -> None:
    left = tmp_path / "left.parquet"
    right = tmp_path / "right.parquet"
    left.write_bytes(b"same")
    right.write_bytes(b"same")

    result = FileArtifactByteComparisonAdapter().compare_artifacts(
        [_ref(left)],
        [_ref(right)],
    )

    assert result["equivalent"] is True
    assert result["semantic_equivalent"] is True
    assert result["raw_byte_equivalent"] is True
    assert result["mismatched_artifacts"] == []


def test_compare_artifacts_reports_raw_byte_mismatch(tmp_path: Path) -> None:
    left = tmp_path / "left.parquet"
    right = tmp_path / "right.parquet"
    left.write_bytes(b"left")
    right.write_bytes(b"right")

    result = FileArtifactByteComparisonAdapter().compare_artifacts(
        [_ref(left)],
        [_ref(right)],
    )

    assert result["equivalent"] is False
    assert result["semantic_equivalent"] is False
    assert result["raw_byte_equivalent"] is False
    assert result["mismatched_artifacts"]
    assert result["raw_byte_mismatched_artifacts"]


def test_compare_artifacts_reports_missing_candidate(tmp_path: Path) -> None:
    left = tmp_path / "left.parquet"
    missing = tmp_path / "missing.parquet"
    left.write_bytes(b"left")

    result = FileArtifactByteComparisonAdapter().compare_artifacts(
        [_ref(left)],
        [_ref(missing)],
    )

    assert result["available"] is True
    assert result["equivalent"] is False
    assert result["missing_artifacts"]


def test_compare_artifacts_treats_occurrence_only_metadata_as_semantic_match(
    tmp_path: Path,
) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text(
        json.dumps({"run_id": "run-a", "manifest_id": "manifest-a", "rows": 10}),
        encoding="utf-8",
    )
    right.write_text(
        json.dumps({"run_id": "run-b", "manifest_id": "manifest-b", "rows": 10}),
        encoding="utf-8",
    )

    result = FileArtifactByteComparisonAdapter().compare_artifacts(
        [_metadata_ref(left)],
        [_metadata_ref(right)],
    )

    assert result["equivalent"] is True
    assert result["semantic_equivalent"] is True
    assert result["raw_byte_equivalent"] is False
    assert result["occurrence_only"] is True
    assert result["occurrence_only_artifacts"]
    assert result["mismatched_artifacts"] == []

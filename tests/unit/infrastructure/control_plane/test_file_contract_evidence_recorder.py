"""Unit tests for the file-backed contract-evidence recorder."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)

pytestmark = pytest.mark.unit


def test_file_recorder_writes_sidecar(tmp_path: Path) -> None:
    recorder = FileContractEvidenceRecorder(base_path=tmp_path)
    recorder.record(
        "manifest-1",
        {
            "contract_comparison_status": "compatible",
            "resume_contract": "resume_not_requested",
        },
    )
    path = tmp_path / "manifest-1.contract-evidence.json"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "compatible" in text
    assert "resume_not_requested" in text


def test_file_recorder_identical_retry_is_noop(tmp_path: Path) -> None:
    recorder = FileContractEvidenceRecorder(base_path=tmp_path)
    evidence = {
        "contract_comparison_status": "compatible",
        "resume_contract": "resume_not_requested",
    }
    recorder.record("manifest-1", evidence)
    first = (tmp_path / "manifest-1.contract-evidence.json").read_text(encoding="utf-8")
    recorder.record("manifest-1", evidence)
    second = (tmp_path / "manifest-1.contract-evidence.json").read_text(
        encoding="utf-8"
    )
    assert first == second


def test_file_recorder_conflict_preserves_original(tmp_path: Path) -> None:
    from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
        ContractEvidenceConflictError,
    )

    recorder = FileContractEvidenceRecorder(base_path=tmp_path)
    recorder.record("manifest-1", {"contract_comparison_status": "compatible"})
    original = (tmp_path / "manifest-1.contract-evidence.json").read_text(
        encoding="utf-8"
    )
    with pytest.raises(ContractEvidenceConflictError):
        recorder.record("manifest-1", {"contract_comparison_status": "UNKNOWN"})
    assert (tmp_path / "manifest-1.contract-evidence.json").read_text(
        encoding="utf-8"
    ) == original

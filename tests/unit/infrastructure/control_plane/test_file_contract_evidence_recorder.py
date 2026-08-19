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

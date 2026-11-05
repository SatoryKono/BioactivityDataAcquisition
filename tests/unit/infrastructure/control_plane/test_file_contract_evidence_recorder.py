"""Unit tests for the file-backed contract-evidence recorder."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)

pytestmark = pytest.mark.unit


def _catalogs(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    live = tmp_path / "live"
    source.mkdir()
    live.mkdir()
    return source, live


def _record(source: Path, live: Path) -> None:
    FileContractEvidenceRecorder(base_path=source, live_catalog=live).record(
        "manifest-1",
        {"contract_comparison_status": "compatible"},
    )


def test_file_recorder_mirrors_sidecar_onto_published_manifest(tmp_path: Path) -> None:
    source, live = _catalogs(tmp_path)
    (live / "manifest-1.json").write_text("{}", encoding="utf-8")
    _record(source, live)
    assert (source / "manifest-1.contract-evidence.json").is_file()
    assert (live / "manifest-1.contract-evidence.json").is_file()


def test_file_recorder_skips_live_copy_without_manifest(tmp_path: Path) -> None:
    source, live = _catalogs(tmp_path)
    _record(source, live)
    assert (source / "manifest-1.contract-evidence.json").is_file()
    assert not (live / "manifest-1.contract-evidence.json").exists()


def test_file_recorder_live_copy_error_keeps_source_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, live = _catalogs(tmp_path)
    (live / "manifest-1.json").write_text("{}", encoding="utf-8")

    def _deny(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("live catalog is read-only")

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_contract_evidence_recorder.copy_contract_evidence_to_live_catalog",
        _deny,
    )
    _record(source, live)
    assert (source / "manifest-1.contract-evidence.json").is_file()


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

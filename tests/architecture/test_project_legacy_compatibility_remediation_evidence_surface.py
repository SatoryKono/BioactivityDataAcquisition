"""Governance checks for the legacy compatibility remediation evidence pack."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
PACK_ROOT = (
    ROOT / "docs" / "reports" / "evidence" / "project-legacy-compatibility-remediation"
)
CANONICAL_CROSS_SYNTHESIS = (
    PACK_ROOT
    / "03-synthesis"
    / "CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md"
)
RECOVERY_PROVENANCE = (
    PACK_ROOT / "06-status" / "recovered-cross-synthesis-provenance-2026-05-21.yaml"
)


def test_canonical_cross_synthesis_is_readable() -> None:
    """The recovered parent synthesis must stay readable by normal tooling."""
    text = CANONICAL_CROSS_SYNTHESIS.read_text(encoding="utf-8")

    assert "Кросс-синтез: project-legacy-compatibility-remediation" in text
    assert "DEC-legacy-use-four-bucket-classification-instead-of-broad-purge" in text
    assert "retain-as-contract" in text
    assert "Wave 1" in text


def test_recovered_cross_synthesis_checksum_matches_provenance() -> None:
    """The recovered synthesis must carry verifiable checksum provenance."""
    manifest = yaml.safe_load(RECOVERY_PROVENANCE.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    artifact_path = ROOT / artifact["path"]

    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    assert digest == artifact["sha256"]
    assert artifact_path.stat().st_size == artifact["byte_size"]
    assert artifact["status"] == "recovered-canonical-copy"

    source_inputs = manifest["source_inputs"]
    assert isinstance(source_inputs, list)
    for source in source_inputs:
        source_path = str(source)
        if "*" in source_path:
            assert list(ROOT.glob(source_path)), (
                f"No provenance inputs match {source_path}"
            )
        else:
            assert (ROOT / source_path).exists(), (
                f"Missing provenance input {source_path}"
            )

    recovery_note = manifest["recovery_note"]
    assert isinstance(recovery_note, dict)
    assert (
        "does not prove byte-for-byte identity" in recovery_note["verification_scope"]
    )


def test_curated_evidence_surface_has_no_unreadable_visible_entries() -> None:
    """Visible curated evidence entries must keep working with standard stat calls."""
    pending = [PACK_ROOT]
    failures: list[str] = []

    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                try:
                    entry.stat(follow_symlinks=False)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                except OSError as exc:
                    failures.append(
                        f"{Path(entry.path).relative_to(ROOT)}: "
                        f"{type(exc).__name__} errno={getattr(exc, 'errno', None)} "
                        f"{exc}"
                    )

    if failures:
        pytest.fail(
            "Curated evidence surface has unreadable visible entries:\n"
            + "\n".join(f"  - {failure}" for failure in failures)
        )

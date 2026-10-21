# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Acceptance for public archive readback without the original sources.

``FileArchiveStore.verify`` re-reads the live data root. After those sources
are removed, the public verify path returns ``archive_evidence_invalid`` even
though the pack still holds the restored bytes. Checksum, identity, and
inventory damage stay covered by the file-archive unit suite.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunManifest,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore

_OBSERVED_AT = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
_LEDGER = '{"event":"retain"}\n'


def _acceptance_case(
    tmp_path: Path,
) -> tuple[FileArchiveStore, RunManifest, ControlPlaneArtifactLifecyclePlan, Path]:
    data_root = tmp_path / "data"
    data_root.mkdir()
    manifest = RunManifest(
        manifest_id="archive-acceptance",
        run_id=RunID(UUID(int=90)),
        pipeline_name="archive-acceptance",
        created_at=_OBSERVED_AT,
        execution_fingerprint="fingerprint-r09",
    )
    manifest_path = data_root / "manifest.json"
    ledger_path = data_root / "ledger.jsonl"
    manifest_path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    ledger_path.write_text(_LEDGER, encoding="utf-8")
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=_OBSERVED_AT,
        cutoff=_OBSERVED_AT,
        dry_run=True,
        artifacts=tuple(
            ControlPlaneArtifactRef(
                surface=surface,
                path=str(path),
                artifact_id="archive-acceptance",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="acceptance",
            )
            for path, surface in (
                (manifest_path, ControlPlaneArtifactSurface.RUN_MANIFEST),
                (ledger_path, ControlPlaneArtifactSurface.RUN_LEDGER),
            )
        ),
    )
    return (
        FileArchiveStore(data_root, tmp_path / "archive"),
        manifest,
        plan,
        ledger_path,
    )


@pytest.mark.integration
def test_public_verify_cannot_read_archive_without_original_sources(
    tmp_path: Path,
) -> None:
    store, manifest, plan, ledger_path = _acceptance_case(tmp_path)
    pack = store.create(manifest=manifest, plan=plan)
    restored = pack / "restored" / "ledger.jsonl"

    assert store.verify(manifest=manifest, plan=plan) == (
        True,
        "archive_restore_verified",
    )
    assert restored.read_text(encoding="utf-8") == ledger_path.read_text(
        encoding="utf-8"
    )

    shutil.rmtree(store.data_root)
    store.data_root.mkdir()

    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_evidence_invalid",
    )
    assert restored.read_text(encoding="utf-8") == _LEDGER


@pytest.mark.integration
def test_explicit_restore_readback_without_original_sources(
    tmp_path: Path,
) -> None:
    store, manifest, plan, _ledger_path = _acceptance_case(tmp_path)
    pack = store.create(manifest=manifest, plan=plan)

    shutil.rmtree(store.data_root)

    # Verify that the explicit restored file still exists and matches expected content
    restored = pack / "restored" / "ledger.jsonl"
    assert restored.exists()
    assert restored.read_text(encoding="utf-8") == _LEDGER


@pytest.mark.integration
def test_concurrent_reference_creation_during_archive_is_preserved(
    tmp_path: Path,
) -> None:
    store, manifest, plan, ledger_path = _acceptance_case(tmp_path)

    # We create the archive, but simulate a concurrent write by modifying the source after creation
    pack = store.create(manifest=manifest, plan=plan)

    # Concurrently write to source
    new_ledger_content = '{"event":"concurrent_update"}\n'
    ledger_path.write_text(new_ledger_content, encoding="utf-8")

    # The archive verify will fail because the source has changed since the archive was created
    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_source_mismatch",
    )

    # The archive itself should still be the old content
    restored = pack / "restored" / "ledger.jsonl"
    assert restored.read_text(encoding="utf-8") == _LEDGER


@pytest.mark.integration
def test_partial_archive_failure_preserves_sources(
    tmp_path: Path,
) -> None:
    store, manifest, _plan, ledger_path = _acceptance_case(tmp_path)

    # Corrupt a source file before archive creation to trigger an error
    # Let's corrupt the plan to ask for a file that does not exist
    bad_plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=_OBSERVED_AT,
        cutoff=_OBSERVED_AT,
        dry_run=True,
        artifacts=tuple(
            ControlPlaneArtifactRef(
                surface=surface,
                path=str(path) + "_nonexistent",
                artifact_id="archive-acceptance",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="acceptance",
            )
            for path, surface in (
                (ledger_path, ControlPlaneArtifactSurface.RUN_LEDGER),
            )
        ),
    )

    with pytest.raises(FileNotFoundError, match="No such file or directory"):
        store.create(manifest=manifest, plan=bad_plan)

    # Verify original source still exists
    assert ledger_path.exists()

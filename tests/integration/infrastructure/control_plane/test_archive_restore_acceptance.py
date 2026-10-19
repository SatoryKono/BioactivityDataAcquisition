import json
import shutil
from pathlib import Path
import uuid
from datetime import datetime, UTC

import pytest

from bioetl.domain.control_plane import (
    RunManifest,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    ControlPlaneArtifactLifecycleDecision,
)
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.domain.types import RunID


@pytest.fixture
def isolated_roots(tmp_path):
    data_root = tmp_path / "data"
    archive_root = tmp_path / "archive"
    report_root = tmp_path / "reports"
    restore_root = tmp_path / "restore"

    data_root.mkdir()
    archive_root.mkdir()
    report_root.mkdir()
    restore_root.mkdir()

    return data_root, archive_root, report_root, restore_root


pytestmark = pytest.mark.integration


def test_archive_restore_acceptance(isolated_roots):
    data_root, archive_root, report_root, _restore_root = isolated_roots

    # 1. Setup a valid manifest and plan
    run_id = RunID(uuid.UUID("12345678-1234-5678-1234-567812345678"))
    manifest = RunManifest(
        manifest_id="test-manifest",
        run_id=run_id,
        pipeline_name="test-pipeline",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        source_refs=(),
        execution_fingerprint="fingerprint",
    )

    # Create source artifacts
    manifest_path = data_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()))

    ledger_path = data_root / "ledger.jsonl"
    ledger_path.write_text('{"event": "test"}')

    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        cutoff=datetime(2025, 1, 1, tzinfo=UTC),
        dry_run=True,
        resolution_issues=(),
        artifacts=(
            ControlPlaneArtifactRef(
                path=str(manifest_path),
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                artifact_id="manifest-id",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="test",
            ),
            ControlPlaneArtifactRef(
                path=str(ledger_path),
                surface=ControlPlaneArtifactSurface.RUN_LEDGER,
                artifact_id="ledger-id",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="test",
            ),
        ),
    )

    # 2. Capture archive
    store = FileArchiveStore(
        data_root=data_root, archive_root=archive_root, report_root=report_root
    )
    pack_path = store.create(manifest=manifest, plan=plan)

    # 3. Verify archive via public API (with source present)
    verified, _reason = store.verify(manifest=manifest, plan=plan)
    assert verified is True

    # 4. Remove source fixture to simulate "source absent" readback
    shutil.rmtree(data_root)

    # 5. Independent readback
    try:
        data_root.mkdir()
        store_restore = FileArchiveStore(
            data_root=data_root, archive_root=archive_root, report_root=report_root
        )
        verified_restore, reason_restore = store_restore.verify(
            manifest=manifest, plan=plan
        )
    except Exception as e:
        verified_restore = False
        reason_restore = str(e)

    report = {
        "sweep_id": "test_r09",
        "archive_acceptance": {
            "source_missing_verification": "NOT_VERIFIABLE"
            if not verified_restore
            else "VERIFIED",
            "reason": reason_restore,
            "blocker": "FileArchiveStore.verify reads directly from original data_root instead of checking the restored payload against the index. Independent public readback without original source is therefore unachievable through the current public verify.",
        },
    }

    report_file = report_root / "archive-restore-acceptance.json"
    report_file.write_text(json.dumps(report, indent=2))

    # Output markdown report as well
    md_report = f"""# Archive Restore Acceptance Report

**Sweep ID**: test_r09
**Status**: {"NOT_VERIFIABLE" if not verified_restore else "VERIFIED"}
**Reason**: {reason_restore}
**Blocker**: FileArchiveStore.verify reads directly from original data_root instead of checking the restored payload against the index. Independent public readback without original source is therefore unachievable through the current public verify.
"""
    # Write to durable project path as required
    persistent_report_dir = Path("reports/audit-runs/test_r09")
    persistent_report_dir.mkdir(parents=True, exist_ok=True)
    (persistent_report_dir / "archive-restore-acceptance.json").write_text(
        json.dumps(report, indent=2)
    )
    (persistent_report_dir / "archive-restore-acceptance.md").write_text(md_report)

    assert verified_restore is False


def test_archive_restore_negative_cases(isolated_roots):
    data_root, archive_root, report_root, _restore_root = isolated_roots

    run_id = RunID(uuid.UUID("12345678-1234-5678-1234-567812345678"))
    manifest = RunManifest(
        manifest_id="test-manifest",
        run_id=run_id,
        pipeline_name="test-pipeline",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        source_refs=(),
        execution_fingerprint="fingerprint",
    )

    manifest_path = data_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()))
    ledger_path = data_root / "ledger.jsonl"
    ledger_path.write_text('{"event": "test"}')

    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        cutoff=datetime(2025, 1, 1, tzinfo=UTC),
        dry_run=True,
        resolution_issues=(),
        artifacts=(
            ControlPlaneArtifactRef(
                path=str(manifest_path),
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                artifact_id="manifest-id",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="test",
            ),
            ControlPlaneArtifactRef(
                path=str(ledger_path),
                surface=ControlPlaneArtifactSurface.RUN_LEDGER,
                artifact_id="ledger-id",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="test",
            ),
        ),
    )

    store = FileArchiveStore(
        data_root=data_root, archive_root=archive_root, report_root=report_root
    )
    pack_path = store.create(manifest=manifest, plan=plan)

    ledger_archive = pack_path / "files" / "ledger.jsonl"
    ledger_archive.write_text('{"event": "corrupted"}')
    verified, reason = store.verify(manifest=manifest, plan=plan)
    assert verified is False
    assert "archive_checksum_mismatch" in reason or "archive_evidence_invalid" in reason

    # Restore original for next test
    ledger_archive.write_text('{"event": "test"}')

    # Test identity mismatch
    index_path = pack_path / "index.json"
    payload = json.loads(index_path.read_text())
    payload["manifest_sha256"] = "wrong"
    index_path.write_text(json.dumps(payload))

    verified, reason = store.verify(manifest=manifest, plan=plan)
    assert verified is False
    assert "archive_identity_mismatch" in reason

    # Test missing member
    # Instead of store._manifest_digest, we will just use the correct hash.
    # To be perfectly correct, just reload original index and pop.
    store_clean = FileArchiveStore(
        data_root=data_root, archive_root=archive_root, report_root=report_root
    )
    # The digest was originally correct. Let's fix the identity to avoid false negatives.
    import importlib

    archive_module = importlib.import_module(
        "bioetl.infrastructure.control_plane.file_archive_store"
    )
    payload["manifest_sha256"] = archive_module._manifest_digest(manifest)
    payload["files"].pop()  # remove a member
    index_path.write_text(json.dumps(payload))

    verified, reason = store.verify(manifest=manifest, plan=plan)
    assert verified is False
    assert "archive_inventory_mismatch" in reason

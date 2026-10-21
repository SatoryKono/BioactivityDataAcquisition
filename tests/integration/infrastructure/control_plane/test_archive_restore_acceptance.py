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
from bioetl.infrastructure.control_plane import file_archive_store

_OBSERVED_AT = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
_LEDGER = '{"event":"retain"}\n'


def _acceptance_case(
    tmp_path: Path,
) -> tuple[
    file_archive_store.FileArchiveStore,
    RunManifest,
    ControlPlaneArtifactLifecyclePlan,
    Path,
]:
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
        file_archive_store.FileArchiveStore(data_root, tmp_path / "archive"),
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
def test_verify_readback_when_data_root_directory_is_gone(
    tmp_path: Path,
) -> None:
    """Public verify fails closed when the data root itself has been removed."""
    store, manifest, plan, _ledger_path = _acceptance_case(tmp_path)
    pack = store.create(manifest=manifest, plan=plan)

    shutil.rmtree(store.data_root)

    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_evidence_invalid",
    )
    assert (pack / "restored" / "ledger.jsonl").read_text(encoding="utf-8") == _LEDGER


@pytest.mark.integration
def test_source_change_during_copy_does_not_publish_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source rewrite between the two digests aborts archive publication."""
    store, manifest, plan, ledger_path = _acceptance_case(tmp_path)
    real_copy = file_archive_store.shutil.copyfile

    def copy_then_rewrite(source: Path, destination: Path) -> Path:
        copied = real_copy(source, destination)
        if source == ledger_path:
            ledger_path.write_text('{"event":"concurrent"}\n', encoding="utf-8")
        return copied

    monkeypatch.setattr(file_archive_store.shutil, "copyfile", copy_then_rewrite)

    with pytest.raises(ValueError, match="archive_source_changed"):
        store.create(manifest=manifest, plan=plan)

    assert ledger_path.is_file()
    assert not (store._pack(manifest) / "index.json").exists()


@pytest.mark.integration
def test_copy_failure_preserves_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure after copying has started leaves the live sources unchanged."""
    store, manifest, plan, ledger_path = _acceptance_case(tmp_path)
    manifest_path = ledger_path.parent / "manifest.json"
    before = {path: path.read_bytes() for path in (ledger_path, manifest_path)}
    real_copy = file_archive_store.shutil.copyfile
    calls = {"count": 0}

    def copy_then_fail(source: Path, destination: Path) -> Path:
        calls["count"] += 1
        if calls["count"] > 1:
            raise OSError("injected copy failure")
        return real_copy(source, destination)

    monkeypatch.setattr(file_archive_store.shutil, "copyfile", copy_then_fail)

    with pytest.raises(OSError, match="injected copy failure"):
        store.create(manifest=manifest, plan=plan)

    for path, payload in before.items():
        assert path.read_bytes() == payload
    assert not (store._pack(manifest) / "index.json").exists()

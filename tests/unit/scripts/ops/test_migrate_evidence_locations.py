from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from bioetl.domain.control_plane.run_manifest import RunManifest, RunType
from bioetl.domain.control_plane.workflow_manifest import WorkflowManifest
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from scripts.engineering.common.repo_paths import REPO_ROOT
from scripts.ops.runtime.migrate_evidence_locations import (
    MigrationTarget,
    execute_migration,
    main,
    read_target_list,
)

_VALID_DIGEST = "0" * 64
_RUN_ID = "00000000-0000-0000-0000-000000000000"
_CREATED_AT = datetime(2024, 1, 1, tzinfo=UTC)


def _workflow_target(
    *,
    runtime_source_id: str = _VALID_DIGEST,
    run_id: str = _RUN_ID,
    relative_data_root: str = "path/to/data",
    owner: str = "test_workflow",
) -> MigrationTarget:
    return MigrationTarget(
        kind=EvidenceLocationKind.WORKFLOW,
        owner=owner,
        run_id=run_id,
        runtime_source_id=runtime_source_id,
        relative_data_root=relative_data_root,
    )


def _seed_workflow_anchors(
    alias_base: Path,
    target: MigrationTarget,
    *,
    owner: str | None = None,
    runtime_source_id: str | None = None,
) -> Path:
    """Materialize workflow manifest anchors under the alias base."""
    data_root = alias_base.joinpath(*target.relative_data_root.split("/"))
    data_root.mkdir(parents=True, exist_ok=True)
    store = FileWorkflowManifestStore(
        base_path=data_root / "output" / "control" / "workflow_manifest"
    )
    source = (
        runtime_source_id if runtime_source_id is not None else target.runtime_source_id
    )
    store.save(
        WorkflowManifest(
            manifest_id=f"wf-{target.run_id}",
            workflow_run_id=RunID(UUID(target.run_id)),
            execution_fingerprint="fp",
            schema_version="1.0",
            created_at=_CREATED_AT,
            workflow_name=owner if owner is not None else target.owner,
            workflow_version="1",
            launch_context={"runtime_source_id": source},
            defaults={},
            selected_step_ids=(),
            steps=(),
        )
    )
    return data_root


def _seed_pipeline_anchors(
    alias_base: Path,
    target: MigrationTarget,
) -> Path:
    data_root = alias_base.joinpath(*target.relative_data_root.split("/"))
    data_root.mkdir(parents=True, exist_ok=True)
    store = FileRunManifestStore(
        base_path=data_root / "output" / "control" / "run_manifest"
    )
    store.save(
        RunManifest(
            manifest_id=f"pipe-{target.run_id}",
            execution_fingerprint="fp",
            schema_version="1.0",
            created_at=_CREATED_AT,
            run_id=RunID(UUID(target.run_id)),
            run_type=RunType.INCREMENTAL,
            pipeline_name=target.owner,
            provider="test",
            entity="test",
            launch_context={"runtime_source_id": target.runtime_source_id},
        )
    )
    return data_root


def test_execute_migration_dry_run_plans_missing(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()
    target = _workflow_target()
    _seed_workflow_anchors(alias_base, target)

    stats = execute_migration(
        [target],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["registered"] == 1
    assert stats["invalid"] == 0
    assert stats["conflict"] == 0
    assert stats["location_invalid"] == 0
    assert stats["binding_mismatch"] == 0


def test_execute_migration_dry_run_flags_invalid(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()

    stats = execute_migration(
        [_workflow_target(runtime_source_id="bad")],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["invalid"] == 1
    assert stats["registered"] == 0


def test_execute_migration_dry_run_rejects_missing_data_root(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()

    stats = execute_migration(
        [_workflow_target()],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["location_invalid"] == 1
    assert stats["registered"] == 0


def test_execute_migration_dry_run_rejects_owner_mismatch(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()
    target = _workflow_target()
    _seed_workflow_anchors(alias_base, target, owner="other_owner")

    stats = execute_migration(
        [target],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["binding_mismatch"] == 1
    assert stats["registered"] == 0


def test_execute_migration_dry_run_rejects_runtime_source_mismatch(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()
    target = _workflow_target()
    _seed_workflow_anchors(
        alias_base,
        target,
        runtime_source_id="a" * 64,
    )

    stats = execute_migration(
        [target],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["binding_mismatch"] == 1
    assert stats["registered"] == 0


def test_execute_migration_dry_run_flags_intra_batch_conflict(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()

    first = _workflow_target()
    second = MigrationTarget(
        kind=first.kind,
        owner=first.owner,
        run_id=first.run_id,
        runtime_source_id=first.runtime_source_id,
        relative_data_root="other/path",
    )
    _seed_workflow_anchors(alias_base, first)
    _seed_workflow_anchors(alias_base, second)

    stats = execute_migration(
        [first, second],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["registered"] == 1
    assert stats["conflict"] == 1


def test_execute_migration_dry_run_normalizes_owner_whitespace(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()

    first = _workflow_target()
    second = MigrationTarget(
        kind=first.kind,
        owner=f" {first.owner} ",
        run_id=first.run_id,
        runtime_source_id=first.runtime_source_id,
        relative_data_root=first.relative_data_root,
    )
    _seed_workflow_anchors(alias_base, first)

    stats = execute_migration(
        [first, second],
        report_root=report_root,
        data_root=alias_base,
        dry_run=True,
    )
    assert stats["registered"] == 1
    assert stats["already_identical"] == 1
    assert stats["conflict"] == 0


def test_execute_migration_apply(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()
    targets = [_workflow_target()]
    _seed_workflow_anchors(alias_base, targets[0])

    stats = execute_migration(
        targets,
        report_root=report_root,
        data_root=alias_base,
        dry_run=False,
    )
    assert stats["registered"] == 1

    # Idempotency
    stats = execute_migration(
        targets,
        report_root=report_root,
        data_root=alias_base,
        dry_run=False,
    )
    assert stats["already_identical"] == 1


def test_execute_migration_apply_rejects_invalid_runtime_source_id(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()

    stats = execute_migration(
        [_workflow_target(runtime_source_id="not-a-digest")],
        report_root=report_root,
        data_root=alias_base,
        dry_run=False,
    )
    assert stats["invalid"] == 1
    assert stats["registered"] == 0


def test_execute_migration_apply_pipeline_anchors(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    alias_base = tmp_path / "data"
    alias_base.mkdir()
    target = MigrationTarget(
        kind=EvidenceLocationKind.PIPELINE,
        owner="chembl_assay",
        run_id=_RUN_ID,
        runtime_source_id=_VALID_DIGEST,
        relative_data_root="wf/chembl_assay",
    )
    _seed_pipeline_anchors(alias_base, target)

    stats = execute_migration(
        [target],
        report_root=report_root,
        data_root=alias_base,
        dry_run=False,
    )
    assert stats["registered"] == 1


def test_read_target_list_rejects_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "escape.json"
    outside.write_text('{"targets": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="refusing path outside"):
        read_target_list(outside, root=REPO_ROOT)


def test_read_target_list_rejects_missing_targets_key(tmp_path: Path) -> None:
    targets_file = tmp_path / "targets.json"
    targets_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a 'targets' array"):
        read_target_list(targets_file, root=tmp_path)


def test_read_target_list_accepts_confined_path(tmp_path: Path) -> None:
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "kind": "workflow",
                        "owner": "demo",
                        "run_id": "00000000-0000-0000-0000-000000000001",
                        "runtime_source_id": "a" * 64,
                        "relative_data_root": "demo/data",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    targets = read_target_list(targets_file, root=tmp_path)
    assert len(targets) == 1
    assert targets[0].owner == "demo"


def test_main_rejects_targets_path_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "escape.json"
    outside.write_text('{"targets": []}', encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert main(["--targets", str(outside), "--data-root", "data"]) == 1


from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from scripts.ops.runtime.migrate_evidence_locations import execute_migration, MigrationTarget

def test_execute_migration_dry_run(tmp_path):
    report_root = tmp_path / "reports"
    report_root.mkdir()

    targets = [
        MigrationTarget(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="test_workflow",
            run_id="00000000-0000-0000-0000-000000000000",
            runtime_source_id="0000000000000000000000000000000000000000000000000000000000000000",
            relative_data_root="path/to/data",
        )
    ]

    stats = execute_migration(targets, report_root=report_root, dry_run=True)
    assert sum(stats.values()) == 0

def test_execute_migration_apply(tmp_path):
    report_root = tmp_path / "reports"
    report_root.mkdir()

    targets = [
        MigrationTarget(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="test_workflow",
            run_id="00000000-0000-0000-0000-000000000000",
            runtime_source_id="0000000000000000000000000000000000000000000000000000000000000000",
            relative_data_root="path/to/data",
        )
    ]

    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["registered"] == 1

    # Idempotency
    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["already_identical"] == 1

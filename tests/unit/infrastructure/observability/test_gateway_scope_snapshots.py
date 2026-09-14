"""Regression coverage for successive process snapshots in Pushgateway."""

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

from bioetl.infrastructure.observability._metrics_gateway_snapshots import (
    partition_snapshots,
)


def _registry(run_type: str, *, workflow: bool = False) -> CollectorRegistry:
    registry = CollectorRegistry()
    Counter("records", "Observed records", ["pipeline", "run_type"], registry=registry).labels(
        "chembl_assay", run_type
    ).inc(1000)
    Gauge("checkpoint", "Persisted checkpoint", ["pipeline"], registry=registry).labels(
        "chembl_assay"
    ).set(123)
    Gauge("process_state", "Process state", registry=registry).set(1)
    if workflow:
        Gauge("workflow_status", "Workflow status", ["workflow"], registry=registry).labels(
            "chembl_baseline"
        ).set(0)
    return registry


def test_standalone_snapshot_preserves_backfill_and_workflow() -> None:
    groups = {}
    for registry in (_registry("backfill", workflow=True), _registry("incremental")):
        for job, group, snapshot in partition_snapshots(registry, job="bioetl"):
            groups[(job, tuple(group.items()))] = snapshot
    exposition = b"".join(generate_latest(snapshot) for snapshot in groups.values())
    assert b'run_type="backfill"' in exposition
    assert b'run_type="incremental"' in exposition
    assert b'workflow_status{workflow="chembl_baseline"} 0.0' in exposition
    assert exposition.count(b'checkpoint{pipeline="chembl_assay"}') == 1


def test_samples_keep_metadata_and_do_not_mutate_registry() -> None:
    registry = _registry("backfill", workflow=True)
    before = generate_latest(registry)
    snapshots = partition_snapshots(registry, job="bioetl")
    assert snapshots[0][0:2] == ("bioetl", {})
    assert generate_latest(registry) == before
    scoped = next(s for _, group, s in snapshots if group.get("run_type") == "backfill")
    text = generate_latest(scoped)
    assert b"# HELP records_total Observed records" in text
    assert b"# TYPE records_total counter" in text
    assert b'1000.0' in text


def test_planned_workflow_snapshot_does_not_replace_pipeline_group() -> None:
    registry = CollectorRegistry()
    Gauge("workflow_expected", "Planned", ["workflow", "pipeline", "run_type"], registry=registry).labels(
        "chembl_baseline", "chembl_assay", "backfill"
    ).set(1)
    snapshots = partition_snapshots(registry, job="bioetl")
    assert len(snapshots) == 1
    assert snapshots[0][0] == "bioetl_workflow_chembl_baseline"
    assert snapshots[0][1] == {"pipeline": "chembl_assay", "run_type": "backfill"}

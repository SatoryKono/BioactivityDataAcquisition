"""Stream B APP: leftover FK reconcile transform branches."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.workflow.transforms import reconcile_foreign_keys as rec
from bioetl.domain.workflow import WorkflowTransformSpec

pytestmark = pytest.mark.unit


def _spec(**config: object) -> WorkflowTransformSpec:
    return WorkflowTransformSpec(
        step_id="s1",
        transform_name="reconcile_foreign_keys",
        config=config or {"action": "delete_orphans"},
    )


def test_build_payload_blocked_reason_and_dry_run() -> None:
    request = SimpleNamespace(
        workflow_run_id="wr",
        manifest_id="m",
        source_keys=None,
        source_key="id",
        source_run_ids=(),
        source_scope="all_current",
        reference_keys=None,
        reference_key="id",
        nulls_equal=True,
        reference_completeness="complete",
    )
    result = SimpleNamespace(
        source_table="src",
        reference_table="ref",
        source_key="id",
        reference_key="id",
        source_layer="silver",
        reference_layer="silver",
        mutation_layer="silver",
        action="delete_orphans",
        scanned_rows=1,
        retained_rows=1,
        orphan_rows_deleted=0,
        mutated=False,
        dry_run=True,
        would_mutate=True,
        mutation_mode="preview",
        quarantine_batch_id=None,
        quarantine_rows_written=0,
        quarantine_error_code=None,
        mutation_blocked_reason="policy",
        source_snapshot={"k": 1},
    )
    payload = rec._build_reconcile_payload(
        spec=_spec(),
        request=request,  # type: ignore[arg-type]
        result=result,
        workflow_name="wf",
    )
    assert payload["mutation_blocked_reason"] == "workflow_dry_run"
    assert payload["source_snapshot"] == {"k": 1}


def test_persist_artifact_missing_ids_and_noncallable_writer() -> None:
    spec = _spec()

    async def _run() -> None:
        logger = SimpleNamespace(debug=lambda *_a, **_k: None)
        ctx = SimpleNamespace(
            artifact_sink=object(),
            workflow_name=None,
            workflow_run_id=None,
            manifest_id=None,
            logger=logger,
        )
        assert (
            await rec._persist_reconcile_result_artifact(
                ctx,  # type: ignore[arg-type]
                spec=spec,
                payload={},
            )
            == ()
        )
        ctx.workflow_name = "wf"
        ctx.workflow_run_id = "wr"
        ctx.manifest_id = "m"
        ctx.artifact_sink = SimpleNamespace(write_reconcile_result_artifact="nope")
        assert (
            await rec._persist_reconcile_result_artifact(
                ctx,  # type: ignore[arg-type]
                spec=spec,
                payload={},
            )
            == ()
        )

    import asyncio

    asyncio.run(_run())


def test_source_scope_run_ids_and_completeness_helpers() -> None:
    assert rec._source_scope({"source_scope": "current_run"}) == "current_run"
    with pytest.raises(ValueError, match="source_scope"):
        rec._source_scope({"source_scope": "other"})
    assert rec._payload_run_ids(SimpleNamespace(run_id="r1")) == ("r1",)
    ids = rec._run_ids_from_upstream(
        {"keep": {"run_id": "a"}, "drop": {"run_id": "b"}},
        workflow_run_id="w",
        depends_on=("keep",),
    )
    assert ids == ("w", "a")
    status, identity, version, ref = rec._resolve_reference_completeness(
        {},
        {"step": {"reference_completeness_evidence": {"status": "partial"}}},
        reference_table="targets",
    )
    assert status == "unproven"
    evidence = rec._upstream_completeness_evidence(
        {
            "raw": object(),
            "ok": {
                "reference_completeness_evidence": {
                    "reference_identity": "targets",
                    "status": "complete",
                }
            },
        },
        "targets",
    )
    assert evidence is not None
    with pytest.raises(ValueError, match="requires config.source_table"):
        rec._required_str({}, "source_table")
    assert rec._optional_layer({}, "source_layer", default=None) is None
    with pytest.raises(ValueError, match="source_keys"):
        rec._optional_key_tuple({"source_keys": "id"}, "source_keys")

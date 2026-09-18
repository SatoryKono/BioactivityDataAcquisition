"""Stream B INF: leftover FK-reconciliation branches without Delta writes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    build_reconciliation_result,
)

pytestmark = pytest.mark.unit


def _request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "source_table": "chembl.assay",
        "reference_table": "chembl.target",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ("assay_id",),
        "reference_completeness": "complete",
        "reference_identity": "chembl.target",
        "completeness_evidence_ref": "tests/unit/fk-reference-complete",
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)  # type: ignore[arg-type]


def _adapter() -> SilverForeignKeyReconciliationAdapter:
    return SilverForeignKeyReconciliationAdapter(
        silver_writer=MagicMock(),  # type: ignore[arg-type]
        logger=MagicMock(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_read_reference_rows_wraps_missing_table() -> None:
    adapter = _adapter()

    async def _missing(**_k: object) -> list[dict[str, object]]:
        raise FileNotFoundError("missing")

    adapter._read_rows = _missing  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="reference table not found"):
        await adapter._read_reference_rows(_request())


@pytest.mark.asyncio
async def test_reconcile_loaded_rows_dry_run_and_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    adapter._write_debug_artifacts = MagicMock()  # type: ignore[method-assign]
    adapter._record_metrics = MagicMock()  # type: ignore[method-assign]
    adapter._log = MagicMock()  # type: ignore[method-assign]
    source_rows = [{"assay_id": "A1", "target_id": "T-missing"}]
    reference_rows = [{"target_id": "T1"}]
    dry = await adapter._reconcile_loaded_rows(
        _request(dry_run=True),
        source_rows=source_rows,
        reference_rows=reference_rows,
    )
    assert dry.would_mutate is True
    assert dry.mutated is False
    assert dry.orphan_rows_deleted == 1

    summary = SimpleNamespace(
        mutation_mode="silver_rewrite",
        quarantine_batch_id="q1",
        quarantine_rows_written=1,
        quarantine_error_code=None,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation.apply_reconciliation_mutation",
        AsyncMock(return_value=summary),
    )
    mutated = await adapter._reconcile_loaded_rows(
        _request(dry_run=False),
        source_rows=source_rows,
        reference_rows=reference_rows,
    )
    assert mutated.mutated is True
    assert mutated.mutation_mode == "silver_rewrite"
    adapter._log.assert_called()
    assert mutated.quarantine_batch_id == "q1"


@pytest.mark.asyncio
async def test_debug_artifact_sink_is_invoked() -> None:
    sink = SimpleNamespace(write_reconcile_debug_artifacts=MagicMock())
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=MagicMock(),  # type: ignore[arg-type]
        logger=MagicMock(),  # type: ignore[arg-type]
        artifact_sink=sink,  # type: ignore[arg-type]
    )
    request = _request(
        debug_export_enabled=True,
        workflow_run_id="run-1",
        step_id="step-1",
    )
    result = build_reconciliation_result(
        request,
        scanned_rows=1,
        retained_rows=0,
        orphan_rows_deleted=1,
        mutated=False,
        would_mutate=True,
        mutation_mode="dry_run_preview",
    )
    adapter._write_debug_artifacts(
        request,
        result,
        retained_rows=[],
        orphan_rows=[{"assay_id": "A1"}],
    )
    sink.write_reconcile_debug_artifacts.assert_called_once()

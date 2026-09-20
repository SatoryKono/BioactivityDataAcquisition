# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Facade/canonical parity tests for FK reconciliation (AUD-005).

The application workflow transform
(``application/workflow/transforms/reconcile_foreign_keys.py``) is a documented
facade over the canonical implementation
(``infrastructure/storage/workflow_foreign_key_reconciliation.py``). These
tests pin the parity contract: facade-built requests must be valid canonical
input, and facade payloads must mirror canonical result fields without drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    build_reconcile_foreign_keys_executor,
)
from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)

pytestmark = pytest.mark.integration


def _spec() -> WorkflowTransformSpec:
    return WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
                "reference_completeness_evidence": {
                    "status": "complete",
                    "evidence_ref": "tests/unit/application/workflow/fk-parity",
                },
            },
        )
    )


@dataclass
class _SilverReader:
    rows_by_table: dict[str, list[dict[str, object]]]

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        del columns
        if table_name not in self.rows_by_table:
            raise FileNotFoundError(table_name)
        return [dict(row) for row in self.rows_by_table[table_name]]


@dataclass
class _Logger:
    events: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def info(self, message: str, **context: object) -> None:
        self.events.append(("info", message, dict(context)))

    def warning(self, message: str, **context: object) -> None:
        self.events.append(("warning", message, dict(context)))

    def debug(self, message: str, **context: object) -> None:
        self.events.append(("debug", message, dict(context)))


@dataclass
class _RecordingPort:
    result: ForeignKeyReconciliationResult
    request: ForeignKeyReconciliationRequest | None = None

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        self.request = request
        return self.result


def _canned_result(
    request: ForeignKeyReconciliationRequest,
) -> ForeignKeyReconciliationResult:
    return ForeignKeyReconciliationResult(
        source_table=request.source_table,
        reference_table=request.reference_table,
        source_key=request.source_key,
        reference_key=request.reference_key,
        action=request.action,
        scanned_rows=0,
        retained_rows=0,
        orphan_rows_deleted=0,
        mutated=False,
        source_layer=request.source_layer,
        reference_layer=request.reference_layer,
        mutation_layer=request.effective_mutation_layer,
        dry_run=request.dry_run,
        would_mutate=False,
    )


def _dry_run_request() -> ForeignKeyReconciliationRequest:
    return ForeignKeyReconciliationRequest(
        source_table="chembl_assay",
        reference_table="chembl_target",
        source_key="target_id",
        reference_key="target_id",
        primary_keys=("assay_id",),
        action="delete_orphans",
        source_layer="silver",
        reference_layer="silver",
        dry_run=True,
        reference_completeness="complete",
        reference_identity="chembl_target",
        completeness_evidence_ref="tests/unit/application/workflow/fk-parity",
    )


_MIRRORED_RESULT_FIELDS = (
    "source_table",
    "reference_table",
    "source_key",
    "reference_key",
    "source_layer",
    "reference_layer",
    "mutation_layer",
    "action",
    "scanned_rows",
    "retained_rows",
    "orphan_rows_deleted",
    "mutated",
    "dry_run",
    "would_mutate",
    "mutation_mode",
    "quarantine_batch_id",
    "quarantine_rows_written",
    "quarantine_error_code",
    "unproven_unmatched_rows",
)


@pytest.mark.asyncio
async def test_facade_request_is_valid_canonical_adapter_input() -> None:
    """Facade-built requests must be accepted by the canonical adapter."""
    port_holder: dict[str, ForeignKeyReconciliationRequest | None] = {"request": None}

    async def _capture(
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        port_holder["request"] = request
        return _canned_result(request)

    capture_port = SimpleNamespace(reconcile_foreign_keys=_capture)
    executor = build_reconcile_foreign_keys_executor(capture_port)

    await executor(_spec(), upstream_outputs={})

    request = port_holder["request"]
    assert request is not None
    assert request.source_table == "chembl_assay"
    assert request.reference_table == "chembl_target"
    assert request.source_key == "target_id"
    assert request.reference_key == "target_id"
    assert request.primary_keys == ("assay_id",)
    assert request.action == "delete_orphans"
    assert request.source_layer == "silver"
    assert request.reference_layer == "silver"
    assert request.source_scope == "all_current"
    assert request.reference_completeness == "complete"
    assert request.dry_run is False

    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverReader({"chembl_assay": [], "chembl_target": []}),
        logger=_Logger(),
    )
    result = await adapter.reconcile_foreign_keys(request)
    assert result.source_table == request.source_table
    assert result.reference_table == request.reference_table
    assert result.mutation_mode == "no_op"
    assert result.mutated is False


@pytest.mark.asyncio
async def test_facade_payload_mirrors_canonical_result_fields() -> None:
    """Facade payloads must mirror canonical result fields without drift."""
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverReader(
            {
                "chembl_assay": [
                    {"assay_id": "a1", "target_id": "t1"},
                    {"assay_id": "a2", "target_id": "MISSING"},
                ],
                "chembl_target": [{"target_id": "t1"}],
            }
        ),
        logger=_Logger(),
    )
    request = _dry_run_request()
    result = await adapter.reconcile_foreign_keys(request)
    assert result.scanned_rows == 2
    assert result.retained_rows == 1
    assert result.orphan_rows_deleted == 1
    assert result.mutated is False
    assert result.would_mutate is True
    assert result.mutation_mode == "dry_run_preview"

    port = _RecordingPort(result=result)
    executor = build_reconcile_foreign_keys_executor(port)
    payload = await executor(
        _spec(), upstream_outputs={}, runtime_context=SimpleNamespace(dry_run=True)
    )

    assert port.request is not None
    assert port.request.dry_run is True
    for field_name in _MIRRORED_RESULT_FIELDS:
        assert payload[field_name] == getattr(result, field_name), field_name
    assert payload["source_keys"] == ["target_id"]
    assert payload["reference_keys"] == ["target_id"]
    assert payload["source_run_ids"] == []
    assert payload["source_scope"] == "all_current"
    assert payload["nulls_equal"] is False
    assert payload["reference_completeness"] == "complete"
    assert "source_snapshot" not in payload


@pytest.mark.asyncio
async def test_dry_run_blocked_reason_parity() -> None:
    """Canonical dry-run results must surface the facade dry-run marker."""
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverReader(
            {
                "chembl_assay": [{"assay_id": "a1", "target_id": "MISSING"}],
                "chembl_target": [{"target_id": "t1"}],
            }
        ),
        logger=_Logger(),
    )
    result = await adapter.reconcile_foreign_keys(_dry_run_request())
    assert result.dry_run is True
    assert result.would_mutate is True

    port = _RecordingPort(result=result)
    executor = build_reconcile_foreign_keys_executor(port)
    payload = await executor(
        _spec(), upstream_outputs={}, runtime_context=SimpleNamespace(dry_run=True)
    )
    assert payload["mutation_blocked_reason"] == "workflow_dry_run"

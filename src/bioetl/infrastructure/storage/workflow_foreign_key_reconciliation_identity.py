"""Deterministic identity helpers for FK reconciliation quarantine writes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from math import isnan
from uuid import UUID

from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import ForeignKeyReconciliationRequest
from bioetl.domain.types import BatchID, RunID

FOREIGN_KEY_ORPHAN_ERROR_CODE = "FILTERED_OUT_SILVER"
FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE = "FILTERED_OUT_GOLD"


def canonical_reconciliation_value(value: object) -> object:
    """Return deterministic JSON-compatible input for quarantine identities."""
    if isinstance(value, float) and isnan(value):
        return "NaN"
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): canonical_reconciliation_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonical_reconciliation_value(nested) for nested in value]
    return value


def build_quarantine_batch_id(
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> BatchID:
    """Build a deterministic quarantine batch identity for orphan rows."""
    return BatchID(
        deterministic_uuid(
            "infrastructure.workflow_foreign_key_reconciliation.quarantine_batch",
            {
                "action": request.action,
                "nulls_equal": request.nulls_equal,
                "orphan_rows": canonical_reconciliation_value(orphan_rows),
                "reference_keys": list(request.effective_reference_keys),
                "reference_layer": request.reference_layer,
                "reference_table": request.reference_table,
                "mutation_layer": request.effective_mutation_layer,
                "source_keys": list(request.effective_source_keys),
                "source_layer": request.source_layer,
                "source_table": request.source_table,
                "workflow_name": request.workflow_name,
            },
        )
    )


def coerce_optional_run_id(workflow_run_id: str | None) -> RunID | None:
    """Map a workflow run identity to ``RunID`` when it is a UUID."""
    if workflow_run_id is None:
        return None
    try:
        return RunID(UUID(str(workflow_run_id)))
    except (TypeError, ValueError, AttributeError):
        return None


def orphan_error_code(request: ForeignKeyReconciliationRequest) -> str:
    """Return the layer-specific stable quarantine error code."""
    if request.effective_mutation_layer == "gold":
        return FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE
    return FOREIGN_KEY_ORPHAN_ERROR_CODE


__all__ = [
    "FOREIGN_KEY_ORPHAN_ERROR_CODE",
    "FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE",
    "build_quarantine_batch_id",
    "canonical_reconciliation_value",
    "coerce_optional_run_id",
    "orphan_error_code",
]

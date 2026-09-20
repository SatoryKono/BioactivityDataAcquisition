"""Foreign-key reconciliation value objects and request guards (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from bioetl.domain.workflow.foreign_key_reconciliation_models import (
        ForeignKeyReconciliationRequest as ForeignKeyReconciliationRequest,
    )

__all__ = [
    "ForeignKeyReconciliationAction",
    "ForeignKeyReconciliationLayer",
    "ForeignKeyReconciliationMutationMode",
    "ForeignKeyReconciliationRequest",
    "ReferenceCompletenessStatus",
    "normalize_layer",
    "normalize_request_layers",
    "normalize_source_run_ids",
    "require_equal_key_tuple_lengths",
    "require_first_keys_match",
    "require_non_empty_keys_tuples",
    "require_non_empty_primary_keys",
    "require_non_empty_str",
    "require_optional_str",
    "require_source_scope",
    "validate_optional_source_reference_keys_pair",
]


def __getattr__(name: str) -> object:
    """Lazily re-export names moved to the models split (cycle-safe)."""
    if name == "ForeignKeyReconciliationRequest":
        from bioetl.domain.workflow.foreign_key_reconciliation_models import (
            ForeignKeyReconciliationRequest,
        )

        return ForeignKeyReconciliationRequest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

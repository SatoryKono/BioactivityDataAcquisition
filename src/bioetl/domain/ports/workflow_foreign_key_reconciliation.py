"""Ports for workflow-level foreign-key reconciliation transforms."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from typing import Literal, Protocol, runtime_checkable

from bioetl.domain.workflow._foreign_key_reconciliation_guards import (
    normalize_layer,
    normalize_request_layers,
    normalize_source_run_ids,
    require_non_empty_primary_keys,
    require_non_empty_str,
    require_optional_str,
    require_source_scope,
    validate_optional_source_reference_keys_pair,
)

__all__ = [
    "ForeignKeyReconciliationAction",
    "ForeignKeyReconciliationLayer",
    "ForeignKeyReconciliationMutationMode",
    "ForeignKeyReconciliationPort",
    "ForeignKeyReconciliationRequest",
    "ForeignKeyReconciliationResult",
]

ForeignKeyReconciliationLayer = Literal["silver", "gold"]
ForeignKeyReconciliationAction = Literal["delete_orphans"]
ForeignKeyReconciliationMutationMode = Literal[
    "unknown",
    "delete_orphans",
    "dry_run",
    "blocked",
    "no_op",
    "missing_source",
    "dry_run_preview",
    "quarantine_skipped",
    "gold_scd2_expiry",
    "silver_rewrite",
    "quarantine_written",
]


@dataclass(frozen=True, slots=True)
class ForeignKeyReconciliationRequest:
    """Typed request for one foreign-key reconciliation action."""

    source_table: str
    reference_table: str
    source_key: str
    reference_key: str
    primary_keys: tuple[str, ...]
    action: ForeignKeyReconciliationAction = "delete_orphans"
    source_keys: tuple[str, ...] | None = None
    reference_keys: tuple[str, ...] | None = None
    nulls_equal: bool = False
    dry_run: bool = False
    workflow_name: str | None = None
    workflow_run_id: str | None = None
    manifest_id: str | None = None
    step_id: str | None = None
    transform_name: str | None = None
    debug_export_enabled: bool = False
    debug_export_dir: str | None = None
    source_scope: str = "all_current"
    source_run_ids: tuple[str, ...] = ()
    _: KW_ONLY
    source_layer: ForeignKeyReconciliationLayer = "silver"
    reference_layer: ForeignKeyReconciliationLayer = "silver"
    mutation_layer: ForeignKeyReconciliationLayer | None = None

    def __post_init__(self) -> None:
        require_non_empty_str(self.source_table, "source_table")
        require_non_empty_str(self.reference_table, "reference_table")
        require_non_empty_str(self.source_key, "source_key")
        require_non_empty_str(self.reference_key, "reference_key")
        require_non_empty_primary_keys(self.primary_keys)
        source_layer, reference_layer, mutation_layer = normalize_request_layers(
            self.source_layer,
            self.reference_layer,
            self.mutation_layer,
        )
        object.__setattr__(self, "source_layer", source_layer)
        object.__setattr__(self, "reference_layer", reference_layer)
        object.__setattr__(self, "mutation_layer", mutation_layer)
        validate_optional_source_reference_keys_pair(
            source_keys=self.source_keys,
            reference_keys=self.reference_keys,
            source_key=self.source_key,
            reference_key=self.reference_key,
        )
        require_optional_str(self.workflow_name, "workflow_name")
        require_optional_str(self.workflow_run_id, "workflow_run_id")
        require_optional_str(self.manifest_id, "manifest_id")
        require_optional_str(self.step_id, "step_id")
        require_optional_str(self.transform_name, "transform_name")
        require_optional_str(self.debug_export_dir, "debug_export_dir")
        require_source_scope(self.source_scope)
        object.__setattr__(
            self,
            "source_run_ids",
            normalize_source_run_ids(self.source_run_ids),
        )

    @property
    def effective_source_keys(self) -> tuple[str, ...]:
        """Return the canonical source key sequence for the request."""
        return self.source_keys if self.source_keys is not None else (self.source_key,)

    @property
    def effective_reference_keys(self) -> tuple[str, ...]:
        """Return the canonical reference key sequence for the request."""
        return (
            self.reference_keys
            if self.reference_keys is not None
            else (self.reference_key,)
        )

    @property
    def effective_mutation_layer(self) -> ForeignKeyReconciliationLayer:
        """Return the layer mutated by this reconciliation request."""
        return (
            self.mutation_layer
            if self.mutation_layer is not None
            else self.source_layer
        )


@dataclass(frozen=True, slots=True)
class ForeignKeyReconciliationResult:
    """Deterministic result of one foreign-key reconciliation action."""

    source_table: str
    reference_table: str
    source_key: str
    reference_key: str
    action: ForeignKeyReconciliationAction
    scanned_rows: int
    retained_rows: int
    orphan_rows_deleted: int
    mutated: bool
    dry_run: bool = False
    would_mutate: bool = False
    mutation_mode: ForeignKeyReconciliationMutationMode = "unknown"
    quarantine_batch_id: str | None = None
    quarantine_rows_written: int = 0
    quarantine_error_code: str | None = None
    _: KW_ONLY
    source_layer: ForeignKeyReconciliationLayer = "silver"
    reference_layer: ForeignKeyReconciliationLayer = "silver"
    mutation_layer: ForeignKeyReconciliationLayer | None = None

    def __post_init__(self) -> None:
        allowed_actions: frozenset[str] = frozenset({"delete_orphans"})
        if self.action not in allowed_actions:
            raise ValueError(
                f"action must be one of {sorted(allowed_actions)}, got {self.action!r}"
            )
        allowed_modes: frozenset[str] = frozenset(
            {
                "unknown",
                "delete_orphans",
                "dry_run",
                "blocked",
                "no_op",
                "missing_source",
                "dry_run_preview",
                "quarantine_skipped",
                "gold_scd2_expiry",
                "silver_rewrite",
                "quarantine_written",
            }
        )
        if self.mutation_mode not in allowed_modes:
            raise ValueError(
                f"mutation_mode must be one of {sorted(allowed_modes)}, got {self.mutation_mode!r}"
            )
        source_layer = normalize_layer(self.source_layer, "source_layer")
        reference_layer = normalize_layer(self.reference_layer, "reference_layer")
        mutation_layer = normalize_layer(
            self.mutation_layer if self.mutation_layer is not None else source_layer,
            "mutation_layer",
        )
        object.__setattr__(self, "source_layer", source_layer)
        object.__setattr__(self, "reference_layer", reference_layer)
        object.__setattr__(self, "mutation_layer", mutation_layer)


@runtime_checkable
class ForeignKeyReconciliationPort(Protocol):
    """Port for storage-backed foreign-key reconciliation actions."""

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        """Reconcile one source table against one reference table."""
        ...

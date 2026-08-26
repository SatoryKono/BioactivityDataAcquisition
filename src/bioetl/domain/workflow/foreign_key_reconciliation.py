"""Foreign-key reconciliation value objects and request guards (ADR-058)."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from typing import Literal, cast

__all__ = [
    "ForeignKeyReconciliationAction",
    "ForeignKeyReconciliationLayer",
    "ForeignKeyReconciliationMutationMode",
    "ForeignKeyReconciliationRequest",
    "ForeignKeyReconciliationResult",
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


def normalize_layer(
    value: ForeignKeyReconciliationLayer | str,
    field_name: str,
) -> ForeignKeyReconciliationLayer:
    """Normalize a reconciliation storage layer."""
    normalized = str(value).strip().lower()
    if normalized not in {"silver", "gold"}:
        raise ValueError(f"{field_name} must be 'silver' or 'gold'")
    return cast("ForeignKeyReconciliationLayer", normalized)


def require_non_empty_str(value: str, field_name: str) -> None:
    """Validate that a string is non-empty after trimming."""
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def require_optional_str(value: str | None, field_name: str) -> None:
    """Validate optional string-like fields when present."""
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def require_non_empty_primary_keys(primary_keys: tuple[str, ...]) -> None:
    """Validate that primary_keys is non-empty."""
    if not primary_keys:
        raise ValueError("primary_keys cannot be empty")


def require_non_empty_keys_tuples(
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
) -> None:
    """Validate that source_keys/reference_keys are not empty."""
    if not source_keys or not reference_keys:
        raise ValueError("source_keys and reference_keys cannot be empty")


def require_equal_key_tuple_lengths(
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
) -> None:
    """Validate that source_keys and reference_keys have equal cardinality."""
    if len(source_keys) != len(reference_keys):
        raise ValueError("source_keys and reference_keys must have the same length")


def require_first_keys_match(
    *,
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
    source_key: str,
    reference_key: str,
) -> None:
    """Validate that the first tuple entries match the canonical single keys."""
    if source_keys[0].strip() != source_key.strip():
        raise ValueError("source_key must match the first source_keys entry")
    if reference_keys[0].strip() != reference_key.strip():
        raise ValueError("reference_key must match the first reference_keys entry")


def validate_optional_source_reference_keys_pair(
    *,
    source_keys: tuple[str, ...] | None,
    reference_keys: tuple[str, ...] | None,
    source_key: str,
    reference_key: str,
) -> None:
    """Validate optional tuple-form keys while preserving single-key invariants."""
    if source_keys is None:
        if reference_keys is None:
            return
        raise ValueError("source_keys and reference_keys must be provided together")

    if reference_keys is None:
        raise ValueError("source_keys and reference_keys must be provided together")

    require_non_empty_keys_tuples(source_keys, reference_keys)
    require_equal_key_tuple_lengths(source_keys, reference_keys)
    require_first_keys_match(
        source_keys=source_keys,
        reference_keys=reference_keys,
        source_key=source_key,
        reference_key=reference_key,
    )


def normalize_request_layers(
    source_layer: ForeignKeyReconciliationLayer | str,
    reference_layer: ForeignKeyReconciliationLayer | str,
    mutation_layer: ForeignKeyReconciliationLayer | str | None,
) -> tuple[
    ForeignKeyReconciliationLayer,
    ForeignKeyReconciliationLayer,
    ForeignKeyReconciliationLayer | None,
]:
    """Normalize and cross-check reconciliation layers."""
    normalized_source = normalize_layer(source_layer, "source_layer")
    normalized_reference = normalize_layer(reference_layer, "reference_layer")
    normalized_mutation = (
        normalize_layer(mutation_layer, "mutation_layer")
        if mutation_layer is not None
        else None
    )
    if normalized_mutation is not None and normalized_mutation != normalized_source:
        raise ValueError("mutation_layer must match source_layer")
    return normalized_source, normalized_reference, normalized_mutation


def require_source_scope(source_scope: str) -> None:
    """Validate source_scope against the allowed closed set."""
    if source_scope not in {"all_current", "current_run"}:
        raise ValueError(
            f"source_scope must be 'all_current' or 'current_run', got {source_scope!r}"
        )


def normalize_source_run_ids(source_run_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Drop blank source run ids and freeze the remainder."""
    return tuple(str(item) for item in source_run_ids if str(item).strip())


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
        return self.mutation_layer or self.source_layer


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

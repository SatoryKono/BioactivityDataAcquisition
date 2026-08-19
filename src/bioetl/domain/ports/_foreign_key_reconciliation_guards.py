"""Validation helpers for foreign-key reconciliation requests."""

from __future__ import annotations

from typing import Literal, cast

ForeignKeyReconciliationLayer = Literal["silver", "gold"]


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
    if value is None:
        return
    if not value.strip():
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

    present_source_keys = source_keys
    present_reference_keys = reference_keys
    require_non_empty_keys_tuples(present_source_keys, present_reference_keys)
    require_equal_key_tuple_lengths(present_source_keys, present_reference_keys)
    require_first_keys_match(
        source_keys=present_source_keys,
        reference_keys=present_reference_keys,
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

"""Physical schema checks for a frozen target candidate cohort."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from pandera.pandas import DataFrameModel, DataFrameSchema

from bioetl.infrastructure.storage.target_migration_classification_checks import (
    classification_fields,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    GOLD_SCD_COLUMNS as _GOLD_SCD_COLUMNS,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    validate_scd_types as _validate_scd_types,
)

_LEGACY_PHYSICAL_POLICY = "legacy_physical_target_v30_to_v31_v1"
_OMITTABLE_RUNTIME_COLUMNS = {
    "silver": frozenset({"_run_id", "_run_type", "_ingestion_ts"}),
    "gold": frozenset({"_index", "_dq_error", "_dq_warn"}),
}


def _physical_columns(rows: Sequence[Mapping[str, object]]) -> set[str]:
    if not rows:
        raise ValueError("empty physical target cohort")
    columns = set(rows[0])
    if any(set(row) != columns for row in rows):
        raise ValueError("target physical cohort has inconsistent columns")
    return columns


def _physical_policy_id(contract: str, *, legacy: bool) -> str:
    """Name the physical shape without nesting the contract choice."""
    if legacy:
        return _LEGACY_PHYSICAL_POLICY
    if contract == "3.2.0":
        return "target_v32_runtime_shape"
    return "target_v31_runtime_shape"


def validate_physical_projection(
    layer: str,
    model: type[DataFrameModel],
    old: Sequence[Mapping[str, object]],
    new: Sequence[Mapping[str, object]],
    contract: str = "3.1.0",
) -> dict[str, object]:
    """Validate a frozen physical projection without changing runtime schemas.

    Only declared historical technical omissions are permitted. Gold's absent
    nullable description is represented as unknown in the validation view,
    never materialized into the preserved rows or used as invented provenance.
    """
    previous, current = _physical_columns(old), _physical_columns(new)
    added = set(classification_fields(contract))
    if previous.intersection(added):
        raise ValueError("physical target migration requires a legacy V30 cohort")
    if current != previous.union(added):
        message = (
            "candidate physical columns must equal old columns plus the 3.2.0 classification fields"
            if contract == "3.2.0"
            else "candidate physical columns must equal old columns plus nine classification fields"
        )
        raise ValueError(message)
    schema = model.to_schema()
    omissions = sorted(
        _OMITTABLE_RUNTIME_COLUMNS[layer].intersection(schema.columns) - previous
    )
    if omissions:
        schema = schema.remove_columns(omissions)
    frame = pd.DataFrame(new)
    storage = _validate_storage_envelope(layer, previous, old)
    if storage:
        frame = frame.drop(columns=storage)
    nullable_absences = _logical_nullable_absences(layer, previous, schema, frame)
    schema.validate(frame, lazy=True)
    return {
        "policy_id": _physical_policy_id(
            contract,
            legacy=any((omissions, storage, nullable_absences)),
        ),
        "omitted_runtime_columns": omissions,
        "logical_nullable_absences": nullable_absences,
        "storage_envelope_columns": storage,
        "physical_columns_preserved": True,
    }


def _logical_nullable_absences(
    layer: str, previous: set[str], schema: DataFrameSchema, frame: pd.DataFrame
) -> list[str]:
    if layer != "gold" or "description" in previous:
        return []
    if not schema.columns["description"].nullable:
        raise ValueError("Gold description is no longer a nullable logical field")
    frame["description"] = None
    return ["description"]


def _validate_storage_envelope(
    layer: str, columns: set[str], rows: Sequence[Mapping[str, object]]
) -> list[str]:
    storage = columns.intersection(_GOLD_SCD_COLUMNS)
    if not storage:
        return []
    if layer != "gold" or storage != _GOLD_SCD_COLUMNS:
        raise ValueError("unsupported or incomplete target storage envelope")
    for row in rows:
        _validate_scd_types(row)
    return sorted(storage)

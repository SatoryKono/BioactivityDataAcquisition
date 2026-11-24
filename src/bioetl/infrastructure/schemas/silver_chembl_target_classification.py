"""Additive Arrow schemas for the opt-in ChEMBL target 3.1.0 and 3.2.0 profiles."""

from __future__ import annotations

import pyarrow as pa

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA


def _insert_before_dq(base: pa.Schema, names: tuple[str, ...]) -> pa.Schema:
    fields = list(base)
    first_dq = next(
        (
            index
            for index, column in enumerate(fields)
            if column.name.startswith("_dq_")
        ),
        len(fields),
    )
    extra = [pa.field(name, pa.string(), nullable=True) for name in names]
    return pa.schema(
        [*fields[:first_dq], *extra, *fields[first_dq:]],
        metadata=base.metadata,
    )


CHEMBL_TARGET_SCHEMA_V31 = _insert_before_dq(
    CHEMBL_TARGET_SCHEMA, TARGET_CLASSIFICATION_FIELDS
)
CHEMBL_TARGET_SCHEMA_V32 = _insert_before_dq(
    CHEMBL_TARGET_SCHEMA_V31, TARGET_CLASSIFICATION_DETAIL_FIELDS
)

__all__ = ["CHEMBL_TARGET_SCHEMA_V31", "CHEMBL_TARGET_SCHEMA_V32"]

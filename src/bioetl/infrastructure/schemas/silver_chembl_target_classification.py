"""Additive Arrow schema for the opt-in ChEMBL target 3.1.0 profile."""

from __future__ import annotations

import pyarrow as pa

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA


def _target_v31_schema() -> pa.Schema:
    fields = list(CHEMBL_TARGET_SCHEMA)
    first_dq = next(
        (
            index
            for index, column in enumerate(fields)
            if column.name.startswith("_dq_")
        ),
        len(fields),
    )
    extra = [
        pa.field(name, pa.string(), nullable=True)
        for name in TARGET_CLASSIFICATION_FIELDS
    ]
    return pa.schema(
        [*fields[:first_dq], *extra, *fields[first_dq:]],
        metadata=CHEMBL_TARGET_SCHEMA.metadata,
    )


CHEMBL_TARGET_SCHEMA_V31 = _target_v31_schema()

__all__ = ["CHEMBL_TARGET_SCHEMA_V31"]

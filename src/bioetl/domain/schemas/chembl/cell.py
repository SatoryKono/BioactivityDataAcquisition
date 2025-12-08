"""Stub Pandera schema for ChEMBL cell metadata."""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import BaseGeneratedColumnsSchema
from bioetl.domain.transform.normalizers import CHEMBL_ID_REGEX


class CellTableSchema(BaseGeneratedColumnsSchema):
    """Minimal schema for cell entities. Extended fields will be added later."""

    cell_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="ChEMBL ID of the cell line",
    )

    cell_name: Series[str] = pa.Field(
        nullable=True,
        description="Optional descriptive name of the cell line",
    )


__all__ = ["CellTableSchema"]


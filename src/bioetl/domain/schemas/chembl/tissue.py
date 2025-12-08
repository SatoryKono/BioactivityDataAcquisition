"""Stub Pandera schema for ChEMBL tissue metadata."""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import BaseGeneratedColumnsSchema
from bioetl.domain.transform.normalizers import CHEMBL_ID_REGEX


class TissueTableSchema(BaseGeneratedColumnsSchema):
    """Minimal schema for tissue entities. Extended fields will be added later."""

    tissue_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="ChEMBL ID of the tissue record",
    )

    tissue_name: Series[str] = pa.Field(
        nullable=True,
        description="Optional descriptive name of the tissue",
    )


__all__ = ["TissueTableSchema"]


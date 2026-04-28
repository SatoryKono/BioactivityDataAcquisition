# mypy: disable-error-code="misc"
"""Composite molecule Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeGoldCommonSchema,
)


class CompositeMoleculeGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged molecule entity.",
    )

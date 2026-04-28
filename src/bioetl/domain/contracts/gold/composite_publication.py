# mypy: disable-error-code="misc"
"""Composite publication Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeGoldCommonSchema,
)


class CompositePublicationGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Publication in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged publication entity.",
    )

    source: Series[str] = pa.Field(nullable=True, alias="_source")
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

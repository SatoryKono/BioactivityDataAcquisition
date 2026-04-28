# mypy: disable-error-code="misc"
"""Composite activity/assay/target Gold schemas."""

from __future__ import annotations

import pandera.pandas as pa

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeGoldCommonSchema,
)


class CompositeActivityGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Activity in Gold layer."""


class CompositeAssayGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Assay in Gold layer."""


class CompositeTargetGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Target in Gold layer."""

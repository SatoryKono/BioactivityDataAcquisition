"""Pandera schemas for the stage-0 tables."""

from __future__ import annotations

from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series

from .constants import (
    CONTENT_ABSENT,
    CONTENT_INSPECTED_NOT_SELECTED,
    CONTENT_SELECTED,
    PROVENANCE_ESTABLISHED,
    PROVENANCE_UNESTABLISHED,
    REQUIRED_FIELD_IDS,
    SHA256_PATTERN,
    USAGE_CANDIDATE_ONLY,
    USAGE_LEGACY,
    USAGE_LIMIT_WHEN_UNESTABLISHED,
)

__all__ = [
    "ContentCheckSchema",
    "MCodeVersionSchema",
    "ProvenanceMapSchema",
]


class ProvenanceMapSchema(pa.DataFrameModel):
    """Field provenance. Unestablished rows are not ground truth."""

    field_id: Series[str] = pa.Field(isin=list(REQUIRED_FIELD_IDS))
    provenance_status: Series[str] = pa.Field(
        isin=[PROVENANCE_ESTABLISHED, PROVENANCE_UNESTABLISHED],
    )
    source_ref: Series[str] | None = pa.Field(nullable=True)
    source_sha256: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=SHA256_PATTERN,
    )
    rule_or_process: Series[str] | None = pa.Field(nullable=True)
    confirmation_owner: Series[str] | None = pa.Field(nullable=True)
    usage_limit: Series[str] = pa.Field(
        isin=["", USAGE_LEGACY, USAGE_CANDIDATE_ONLY],
    )
    accepted_as_ground_truth: Series[bool] = pa.Field()

    class Config:
        """Strict column set in the published order."""

        strict = True
        ordered = True
        coerce = True

    @pa.dataframe_check
    @classmethod
    def required_fields_once(
        cls,
        frame: DataFrame[ProvenanceMapSchema],
    ) -> bool:
        """Every required field appears once."""
        return sorted(frame["field_id"].tolist()) == sorted(REQUIRED_FIELD_IDS)

    @pa.dataframe_check
    @classmethod
    def unestablished_fields_stay_restricted(
        cls,
        frame: DataFrame[ProvenanceMapSchema],
    ) -> Series[bool]:
        """Missing provenance cannot become ground truth or drop its limit."""
        unestablished = frame["provenance_status"].eq(PROVENANCE_UNESTABLISHED)
        ok = pd.Series(True, index=frame.index)
        ok &= ~unestablished | ~frame["accepted_as_ground_truth"].astype(bool)
        established = ~unestablished
        ok &= ~established | frame["usage_limit"].eq("")
        ok &= ~established | frame["accepted_as_ground_truth"].astype(bool)
        for field_id, limit in USAGE_LIMIT_WHEN_UNESTABLISHED.items():
            masked = unestablished & frame["field_id"].eq(field_id)
            ok &= ~masked | frame["usage_limit"].eq(limit)
        g2p_unestablished = unestablished & frame["field_id"].eq("g2p_availability")
        ok &= ~g2p_unestablished | frame["usage_limit"].eq("")
        return cast(Series[bool], ok)


class MCodeVersionSchema(pa.DataFrameModel):
    """Stage-5 M-code versions. An empty table means the list is not established."""

    version_id: Series[str] = pa.Field(nullable=False)
    source_ref: Series[str] = pa.Field(nullable=False)
    source_sha256: Series[str] = pa.Field(nullable=False, str_matches=SHA256_PATTERN)

    class Config:
        """Strict column set. Empty frames are valid."""

        strict = True
        ordered = True
        coerce = True


class ContentCheckSchema(pa.DataFrameModel):
    """Table-content facts. Status values do not include PASS."""

    check_id: Series[str] = pa.Field(nullable=False, unique=True)
    subject: Series[str] = pa.Field(nullable=False)
    status: Series[str] = pa.Field(
        isin=[CONTENT_ABSENT, CONTENT_INSPECTED_NOT_SELECTED, CONTENT_SELECTED],
    )
    row_count: Series[pd.Int64Dtype] | None = pa.Field(nullable=True, ge=0)
    byte_count: Series[pd.Int64Dtype] | None = pa.Field(nullable=True, ge=0)
    sha256: Series[str] | None = pa.Field(nullable=True, str_matches=SHA256_PATTERN)
    column_count: Series[pd.Int64Dtype] | None = pa.Field(nullable=True, ge=0)
    watched_fields: Series[str] = pa.Field(nullable=False)
    selected_as_stage0_source: Series[bool] = pa.Field()
    note: Series[str] = pa.Field(nullable=False)

    class Config:
        """Strict column set in the published order."""

        strict = True
        ordered = True
        coerce = True

    @pa.dataframe_check
    @classmethod
    def absent_rows_have_no_hash(
        cls,
        frame: DataFrame[ContentCheckSchema],
    ) -> Series[bool]:
        """An absent subject has no hash and is not a selected source."""
        absent = frame["status"].eq(CONTENT_ABSENT)
        ok = pd.Series(True, index=frame.index)
        ok &= ~absent | frame["sha256"].isna()
        ok &= ~absent | ~frame["selected_as_stage0_source"].astype(bool)
        selected = frame["status"].eq(CONTENT_SELECTED)
        ok &= ~selected | frame["selected_as_stage0_source"].astype(bool)
        ok &= ~selected | frame["sha256"].notna()
        return cast(Series[bool], ok)

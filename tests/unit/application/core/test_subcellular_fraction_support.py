"""Unit tests for subcellular_fraction_support (#7787)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bioetl.domain.types import JsonDict

import pytest

from bioetl.application.core.subcellular_fraction_support import (
    extract_unique_fraction_records,
    normalize_fraction,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_extract_unique_fraction_records_consumes_full_stream_with_limit() -> (
    None
):
    """limit caps unique fractions but still aggregates counts from later assays."""

    async def _assays() -> AsyncIterator[JsonDict]:
        yield {
            "assay_chembl_id": "A1",
            "assay_subcellular_fraction": "cytosol",
        }
        yield {
            "assay_chembl_id": "A2",
            "assay_subcellular_fraction": "nucleus",
        }
        # Same fraction as first — must update assay_count even after limit==1.
        yield {
            "assay_chembl_id": "A3",
            "assay_subcellular_fraction": "cytosol",
        }
        # New fraction after limit — must be ignored as a *new* unique, stream continues.
        yield {
            "assay_chembl_id": "A4",
            "assay_subcellular_fraction": "membrane",
        }

    seen: set[str] = set()
    records = [
        record
        async for record in extract_unique_fraction_records(
            _assays(),
            limit=1,
            seen_fractions=seen,
        )
    ]

    assert len(records) == 1
    assert records[0]["subcellular_fraction"].lower() == "cytosol"
    assert records[0]["assay_count"] == 2
    assert records[0]["example_assay_id"] == "A1"
    assert "cytosol" in seen or any(k == "cytosol" for k in seen)


def test_normalize_fraction_accepts_object_and_returns_str_or_none() -> None:
    assert normalize_fraction(None) is None
    assert normalize_fraction(123) is None or isinstance(normalize_fraction(123), str)

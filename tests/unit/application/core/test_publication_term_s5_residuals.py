# pyright: reportArgumentType=false
"""S5 publication_term residual coverage for #7762 #7845 #7846."""

from __future__ import annotations

import pytest

from bioetl.application.core.data_sources.publication_term import (
    PublicationTermDataSource,
)
from bioetl.application.core.publication_term_extraction_mixin import (
    normalize_publication_term_limit,
)
from bioetl.application.core.publication_term_runtime import (
    create_term_record,
    extract_terms_from_publication,
)

pytestmark = pytest.mark.unit


def test_normalize_publication_term_limit_accepts_zero_and_rejects_invalid() -> None:
    assert normalize_publication_term_limit(None) is None
    assert normalize_publication_term_limit(0) == 0
    assert normalize_publication_term_limit(3) == 3
    with pytest.raises(ValueError, match="limit must be >= 0"):
        normalize_publication_term_limit(-1)
    with pytest.raises(TypeError):
        normalize_publication_term_limit(True)  # type: ignore[arg-type]


def test_resolve_target_fallback_upstream_limit_treats_zero_as_zero() -> None:
    class _Src:
        async def fetch(self, **kwargs):  # type: ignore[no-untyped-def]
            if False:
                yield {}
            raise AssertionError("upstream fetch must not run for pure limit math")

    wrapper = PublicationTermDataSource(data_source=_Src())  # type: ignore[arg-type]
    resolve_limit = getattr(wrapper, "_resolve_target_fallback_upstream_limit")
    assert callable(resolve_limit)
    assert resolve_limit(0) == 0
    assert resolve_limit(2) == (
        2 * PublicationTermDataSource.PUBLICATION_LIMIT_MULTIPLIER
    )
    assert resolve_limit(None) is None


@pytest.mark.asyncio
async def test_fetch_limit_zero_yields_empty_without_upstream_records() -> None:
    class _Src:
        def __init__(self) -> None:
            self.calls = 0

        async def fetch(self, **kwargs):  # type: ignore[no-untyped-def]
            self.calls += 1
            if False:
                yield {}

    source = _Src()
    wrapper = PublicationTermDataSource(data_source=source)  # type: ignore[arg-type]
    terms = [term async for term in wrapper.fetch("publication_term", limit=0)]
    assert terms == []
    assert source.calls == 0


def test_extract_mesh_rejects_non_string_and_blank_fields_s5_residual() -> None:
    publication = {
        "mesh_terms": [
            {
                "mesh_heading": "  ",
                "mesh_id": "D1",
                "mesh_qualifier": "use",
            },
            {
                "mesh_heading": 123,
                "mesh_id": "D2",
                "mesh_qualifier": "x",
            },
            {
                "mesh_heading": "kinase",
                "mesh_id": " D004791 ",
                "mesh_qualifier": " therapeutic use ",
            },
        ],
        "keywords": ["ok", "  ", 5, None],
    }
    terms = extract_terms_from_publication(publication, "CHEMBL9")
    assert sum(1 for t in terms if t["term_type"] == "KEYWORD") == 1
    heading = next(t for t in terms if t["term"] == "kinase")
    assert heading["mesh_id"] == "D004791"
    assert heading["qualifier"] == "therapeutic use"
    qualifier = next(t for t in terms if t["term"] == "therapeutic use")
    assert qualifier["term_type"] == "MESH_QUALIFIER"
    # blank heading with qualifier still yields MESH_QUALIFIER only
    assert any(t["term"] == "use" and t["term_type"] == "MESH_QUALIFIER" for t in terms)


def test_create_term_record_normalizes_mesh_id_and_qualifier_s5_residual() -> None:
    record = create_term_record(
        publication_id="CHEMBL1",
        term="enzyme",
        term_type="MESH_HEADING",
        mesh_id="  D1  ",
        qualifier="  use  ",
    )
    assert record["mesh_id"] == "D1"
    assert record["qualifier"] == "use"

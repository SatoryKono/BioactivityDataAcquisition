"""Tests for PubChem query builder functions.

Covers all 6 public endpoint builder functions with expected URL patterns.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.pubchem.query_builder import (
    build_assay_endpoint,
    build_cid_batch_endpoint,
    build_compound_name_endpoint,
    build_inchikey_endpoint,
    build_smiles_endpoint,
    build_substance_name_endpoint,
)


@pytest.mark.unit
class TestBuildCompoundNameEndpoint:
    def test_basic_query(self) -> None:
        result = build_compound_name_endpoint("aspirin")
        assert result == "/compound/name/aspirin/JSON"

    def test_query_with_spaces(self) -> None:
        result = build_compound_name_endpoint("acetic acid")
        assert "compound/name/acetic acid" in result
        assert result.endswith("/JSON")


@pytest.mark.unit
class TestBuildSubstanceNameEndpoint:
    def test_basic_query(self) -> None:
        result = build_substance_name_endpoint("glucose")
        assert result == "/substance/name/glucose/JSON"

    def test_contains_substance(self) -> None:
        result = build_substance_name_endpoint("test")
        assert "substance/name/test" in result


@pytest.mark.unit
class TestBuildAssayEndpoint:
    def test_basic_query(self) -> None:
        result = build_assay_endpoint("12345")
        assert result == "/assay/aid/12345/JSON"

    def test_contains_assay(self) -> None:
        result = build_assay_endpoint("test")
        assert "assay" in result


@pytest.mark.unit
class TestBuildSmilesEndpoint:
    def test_returns_smiles_path(self) -> None:
        result = build_smiles_endpoint()
        assert result == "/compound/smiles/JSON"

    def test_contains_smiles(self) -> None:
        assert "smiles" in build_smiles_endpoint()


@pytest.mark.unit
class TestBuildInchikeyEndpoint:
    def test_returns_inchikey_path(self) -> None:
        result = build_inchikey_endpoint()
        assert result == "/compound/inchikey/JSON"

    def test_contains_inchikey(self) -> None:
        assert "inchikey" in build_inchikey_endpoint()


@pytest.mark.unit
class TestBuildCidBatchEndpoint:
    def test_basic_batch(self) -> None:
        result = build_cid_batch_endpoint([1, 2, 3])
        assert "cid/1,2,3" in result
        assert result.endswith("/JSON")

    def test_single_cid(self) -> None:
        cids = [42]
        assert cids
        result = build_cid_batch_endpoint(cids)
        assert result == "/compound/cid/42/JSON"

    def test_large_batch_truncated_to_preview(self) -> None:
        """Only first 3 CIDs appear in endpoint preview."""
        cids = list(range(1, 101))
        result = build_cid_batch_endpoint(cids)
        assert "cid/1,2,3,..." in result
        assert "100" not in result

    def test_empty_batch_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="at least one CID"):
            build_cid_batch_endpoint([])

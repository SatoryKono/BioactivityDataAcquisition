# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for PubChem response mapper.

Covers:
- normalize_pubchem_results: None, list, tuple, other types
- PubChemResponseMapper: map_compounds, map_substances, map_assays delegation
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.response_mapper import (
    PubChemResponseMapper,
    normalize_pubchem_results,
)


# ---------------------------------------------------------------------------
# normalize_pubchem_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizePubchemResults:
    def test_none_returns_empty_list(self) -> None:
        assert normalize_pubchem_results(None) == []

    def test_list_returned_as_is(self) -> None:
        data = [1, 2, 3]
        assert normalize_pubchem_results(data) == [1, 2, 3]

    def test_pubchem_results__empty_list__7af1c4bf(self) -> None:
        assert normalize_pubchem_results([]) == []

    def test_tuple_converted_to_list(self) -> None:
        assert normalize_pubchem_results((1, 2)) == [1, 2]

    def test_single_element_tuple(self) -> None:
        assert normalize_pubchem_results((42,)) == [42]

    def test_string_returns_empty_list(self) -> None:
        """String is not list/tuple, so returns []."""
        assert normalize_pubchem_results("not a list") == []

    def test_int_returns_empty_list(self) -> None:
        assert normalize_pubchem_results(42) == []

    def test_dict_returns_empty_list(self) -> None:
        assert normalize_pubchem_results({"key": "val"}) == []


# ---------------------------------------------------------------------------
# PubChemResponseMapper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPubChemResponseMapper:
    @pytest.fixture
    def mock_entity_mapper(self) -> MagicMock:
        mapper = MagicMock()
        mapper.compound_to_dict.side_effect = lambda c: {"cid": c.cid}
        mapper.substance_to_dict.side_effect = lambda s: {"sid": s.sid}
        mapper.assay_to_dict.side_effect = lambda a: {
            "aid": a.get("aid") if isinstance(a, dict) else a.aid
        }
        return mapper

    @pytest.fixture
    def response_mapper(self, mock_entity_mapper: MagicMock) -> PubChemResponseMapper:
        return PubChemResponseMapper(mapper=mock_entity_mapper)

    def test_map_compounds_delegates(
        self, response_mapper: PubChemResponseMapper, mock_entity_mapper: MagicMock
    ) -> None:
        c1 = MagicMock(cid=1)
        c2 = MagicMock(cid=2)
        result = response_mapper.map_compounds([c1, c2])
        assert result == [{"cid": 1}, {"cid": 2}]
        assert mock_entity_mapper.compound_to_dict.call_count == 2

    def test_map_compounds_empty(self, response_mapper: PubChemResponseMapper) -> None:
        assert response_mapper.map_compounds([]) == []

    def test_map_substances_delegates(
        self, response_mapper: PubChemResponseMapper, mock_entity_mapper: MagicMock
    ) -> None:
        s1 = MagicMock(sid=10)
        result = response_mapper.map_substances([s1])
        assert result == [{"sid": 10}]
        mock_entity_mapper.substance_to_dict.assert_called_once_with(s1)

    def test_map_assays_delegates(
        self, response_mapper: PubChemResponseMapper, mock_entity_mapper: MagicMock
    ) -> None:
        a1 = {"aid": 100}
        result = response_mapper.map_assays([a1])
        assert result == [{"aid": 100}]
        mock_entity_mapper.assay_to_dict.assert_called_once_with(a1)

    def test_map_assays_empty(self, response_mapper: PubChemResponseMapper) -> None:
        assert response_mapper.map_assays([]) == []

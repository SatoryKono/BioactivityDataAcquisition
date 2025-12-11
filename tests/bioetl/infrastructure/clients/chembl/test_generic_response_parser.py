"""Tests for ChemblGenericResponseParser."""

import warnings

from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
    create_generic_parser,
)


class TestChemblGenericResponseParser:
    """Tests for the new generic parser."""

    def test_implements_port_interface(self):
        """Test that parser implements ResponseParserPortABC."""
        parser = ChemblGenericResponseParser()
        assert isinstance(parser, ResponseParserPortABC)

    def test_parse_to_records_returns_list_of_dicts(self):
        """Test parse_to_records returns list[dict]."""
        parser = ChemblGenericResponseParser()
        response = {
            "activities": [
                {"activity_id": "1", "standard_flag": True},
                {"activity_id": "2", "standard_flag": False},
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse_to_records(response)

        assert isinstance(records, list)
        assert len(records) == 2
        assert all(isinstance(r, dict) for r in records)
        assert records[0]["activity_id"] == "1"
        assert records[1]["activity_id"] == "2"

    def test_parse_to_records_empty_response(self):
        """Test parse_to_records with no list data."""
        parser = ChemblGenericResponseParser()
        response = {"page_meta": {"offset": 0}}
        records = parser.parse_to_records(response)

        assert records == []

    def test_parse_to_records_empty_list(self):
        """Test parse_to_records with empty list."""
        parser = ChemblGenericResponseParser()
        response = {"activities": [], "page_meta": {}}
        records = parser.parse_to_records(response)

        assert records == []

    def test_parse_to_records_molecules(self):
        """Test parse_to_records with molecules data."""
        parser = ChemblGenericResponseParser()
        response = {
            "molecules": [
                {"molecule_chembl_id": "CHEMBL1", "pref_name": "Aspirin"},
                {"molecule_chembl_id": "CHEMBL2"},
            ],
        }
        records = parser.parse_to_records(response)

        assert len(records) == 2
        assert records[0]["molecule_chembl_id"] == "CHEMBL1"
        assert records[0]["pref_name"] == "Aspirin"

    def test_parse_to_records_non_dict_items(self):
        """Test parse_to_records wraps non-dict items."""
        parser = ChemblGenericResponseParser()
        response = {"values": ["item1", "item2", 123]}
        records = parser.parse_to_records(response)

        assert len(records) == 3
        assert records[0] == {"value": "item1"}
        assert records[1] == {"value": "item2"}
        assert records[2] == {"value": 123}

    def test_parse_to_records_preserves_all_fields(self):
        """Test that all fields are preserved without validation."""
        parser = ChemblGenericResponseParser()
        response = {
            "items": [
                {
                    "known_field": "value",
                    "unknown_field": "also preserved",
                    "nested": {"key": "value"},
                    "number": 123,
                    "bool": True,
                    "null": None,
                },
            ],
        }
        records = parser.parse_to_records(response)

        assert len(records) == 1
        record = records[0]
        assert record["known_field"] == "value"
        assert record["unknown_field"] == "also preserved"
        assert record["nested"] == {"key": "value"}
        assert record["number"] == 123
        assert record["bool"] is True
        assert record["null"] is None


class TestExtractPagination:
    """Tests for pagination extraction."""

    def test_extract_pagination_full_metadata(self):
        """Test extract_pagination with full page_meta."""
        parser = ChemblGenericResponseParser()
        response = {
            "activities": [],
            "page_meta": {
                "total_count": 1000,
                "offset": 100,
                "limit": 20,
                "next": "/api/activities?offset=120",
            },
        }
        pagination = parser.extract_pagination(response)

        assert pagination["total_count"] == 1000
        assert pagination["offset"] == 100
        assert pagination["limit"] == 20
        assert pagination["next"] == "/api/activities?offset=120"

    def test_extract_pagination_partial_metadata(self):
        """Test extract_pagination with partial page_meta."""
        parser = ChemblGenericResponseParser()
        response = {
            "page_meta": {
                "offset": 0,
                "limit": 20,
            },
        }
        pagination = parser.extract_pagination(response)

        assert pagination["total_count"] is None
        assert pagination["offset"] == 0
        assert pagination["limit"] == 20
        assert pagination["next"] is None

    def test_extract_pagination_missing_page_meta(self):
        """Test extract_pagination when page_meta is missing."""
        parser = ChemblGenericResponseParser()
        response = {"activities": []}
        pagination = parser.extract_pagination(response)

        assert pagination["total_count"] is None
        assert pagination["offset"] is None
        assert pagination["limit"] is None
        assert pagination["next"] is None

    def test_extract_pagination_invalid_page_meta_type(self):
        """Test extract_pagination when page_meta is not a dict."""
        parser = ChemblGenericResponseParser()
        response = {"page_meta": "invalid"}
        pagination = parser.extract_pagination(response)

        assert pagination["total_count"] is None
        assert pagination["offset"] is None
        assert pagination["limit"] is None
        assert pagination["next"] is None


class TestCreateGenericParser:
    """Tests for create_generic_parser factory."""

    def test_create_generic_parser_returns_correct_type(self):
        """Test factory returns ChemblGenericResponseParser."""
        parser = create_generic_parser()
        assert isinstance(parser, ChemblGenericResponseParser)
        assert isinstance(parser, ResponseParserPortABC)

    def test_create_generic_parser_no_deprecation_warning(self):
        """Test factory does not emit deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_generic_parser()
            deprecation_warnings = [
                x for x in w if issubclass(x.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) == 0


class TestNoDomainImportsAtModuleLevel:
    """Tests to verify domain models are not imported at module level."""

    def test_generic_parser_has_no_domain_model_dependencies(self):
        """Verify ChemblGenericResponseParser doesn't use domain models."""
        import inspect

        source = inspect.getsource(ChemblGenericResponseParser)
        # Should not reference any *RawModel classes
        assert "ActivityRawModel" not in source
        assert "MoleculeRawModel" not in source
        assert "TargetRawModel" not in source


class TestDeprecatedAliases:
    """Tests for deprecated backward-compatibility aliases."""

    def test_chembl_response_parser_impl_alias_emits_warning(self):
        """Test ChemblResponseParserImpl alias emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Import the deprecated alias
            from bioetl.infrastructure.clients.chembl.response_parser import (
                ChemblResponseParserImpl,  # noqa: F401
            )

            deprecation_warnings = [
                x for x in w if issubclass(x.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) == 1
            assert "ChemblResponseParserImpl is deprecated" in str(
                deprecation_warnings[0].message
            )
            assert "ChemblGenericResponseParser" in str(deprecation_warnings[0].message)

    def test_chembl_response_parser_impl_alias_returns_correct_class(self):
        """Test ChemblResponseParserImpl alias returns ChemblGenericResponseParser."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from bioetl.infrastructure.clients.chembl.response_parser import (
                ChemblResponseParserImpl,
            )

            assert ChemblResponseParserImpl is ChemblGenericResponseParser

    def test_deprecated_alias_is_functional(self):
        """Test that deprecated alias creates working parser instances."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from bioetl.infrastructure.clients.chembl.response_parser import (
                ChemblResponseParserImpl,
            )

            parser = ChemblResponseParserImpl()
            response = {"activities": [{"id": "1"}]}
            records = parser.parse_to_records(response)

            assert len(records) == 1
            assert records[0]["id"] == "1"

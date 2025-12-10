"""Tests for parsing port contracts and type aliases."""

from typing import Any

import pytest

from bioetl.domain.ports.parsing import (
    PaginationInfo,
    RawPayload,
    RawRecordDict,
    RawRecordList,
    ResponseParserPortABC,
)


class TestTypeAliases:
    """Tests for type alias compatibility and correctness."""

    def test_raw_payload_accepts_dict(self) -> None:
        """RawPayload should accept dict[str, Any]."""
        payload: RawPayload = {"key": "value", "number": 123, "nested": {"a": 1}}
        assert isinstance(payload, dict)
        assert payload["key"] == "value"

    def test_raw_record_dict_accepts_dict(self) -> None:
        """RawRecordDict should accept dict[str, Any]."""
        record: RawRecordDict = {"id": "123", "name": "test", "value": 42.5}
        assert isinstance(record, dict)
        assert record["id"] == "123"

    def test_raw_record_list_accepts_list_of_dicts(self) -> None:
        """RawRecordList should accept list of record dicts."""
        records: RawRecordList = [
            {"id": "1", "name": "first"},
            {"id": "2", "name": "second"},
        ]
        assert isinstance(records, list)
        assert len(records) == 2
        assert all(isinstance(r, dict) for r in records)

    def test_type_aliases_are_compatible_with_any_values(self) -> None:
        """Type aliases should allow Any values in dicts."""
        payload: RawPayload = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"deep": {"value": "ok"}},
        }
        assert payload["string"] == "value"
        assert payload["nested"]["deep"]["value"] == "ok"


class TestResponseParserPortABC:
    """Tests for ResponseParserPortABC contract."""

    def test_is_abstract_class(self) -> None:
        """ResponseParserPortABC should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            ResponseParserPortABC()  # type: ignore[abstract]

    def test_requires_parse_to_records_method(self) -> None:
        """Implementations must provide parse_to_records method."""

        class IncompleteParser(ResponseParserPortABC):
            def extract_pagination(
                self, raw_response: RawPayload
            ) -> dict[str, int | str | None]:
                return {}

        with pytest.raises(TypeError, match="abstract"):
            IncompleteParser()  # type: ignore[abstract]

    def test_requires_extract_pagination_method(self) -> None:
        """Implementations must provide extract_pagination method."""

        class IncompleteParser(ResponseParserPortABC):
            def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
                return []

        with pytest.raises(TypeError, match="abstract"):
            IncompleteParser()  # type: ignore[abstract]

    def test_complete_implementation_instantiates(self) -> None:
        """Complete implementation should be instantiable."""

        class CompleteParser(ResponseParserPortABC):
            def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
                for value in raw_response.values():
                    if isinstance(value, list):
                        return value
                return []

            def extract_pagination(
                self, raw_response: RawPayload
            ) -> dict[str, int | str | None]:
                return raw_response.get("page_meta", {})

        parser = CompleteParser()
        assert isinstance(parser, ResponseParserPortABC)

    def test_implementation_parses_records(self) -> None:
        """Implementation should correctly parse records from response."""

        class TestParser(ResponseParserPortABC):
            def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
                return raw_response.get("items", [])

            def extract_pagination(
                self, raw_response: RawPayload
            ) -> dict[str, int | str | None]:
                return raw_response.get("meta", {})

        parser = TestParser()
        response: RawPayload = {
            "items": [{"id": "1"}, {"id": "2"}],
            "meta": {"total_count": 100},
        }
        records = parser.parse_to_records(response)

        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[1]["id"] == "2"

    def test_implementation_extracts_pagination(self) -> None:
        """Implementation should correctly extract pagination metadata."""

        class TestParser(ResponseParserPortABC):
            def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
                return []

            def extract_pagination(
                self, raw_response: RawPayload
            ) -> dict[str, int | str | None]:
                meta = raw_response.get("page_meta", {})
                return {
                    "total_count": meta.get("total_count"),
                    "offset": meta.get("offset"),
                    "limit": meta.get("limit"),
                }

        parser = TestParser()
        response: RawPayload = {
            "page_meta": {"total_count": 500, "offset": 0, "limit": 100}
        }
        pagination = parser.extract_pagination(response)

        assert pagination["total_count"] == 500
        assert pagination["offset"] == 0
        assert pagination["limit"] == 100


class TestPaginationInfo:
    """Tests for PaginationInfo value object."""

    def test_default_values(self) -> None:
        """PaginationInfo should have sensible defaults."""
        info = PaginationInfo()
        assert info.total_count is None
        assert info.offset == 0
        assert info.limit == 0
        assert info.next_url is None

    def test_with_all_fields(self) -> None:
        """PaginationInfo should accept all fields."""
        info = PaginationInfo(
            total_count=1000,
            offset=100,
            limit=50,
            next_url="https://api.example.com/next",
        )
        assert info.total_count == 1000
        assert info.offset == 100
        assert info.limit == 50
        assert info.next_url == "https://api.example.com/next"

    def test_is_frozen(self) -> None:
        """PaginationInfo should be immutable."""
        info = PaginationInfo(total_count=100)
        with pytest.raises(AttributeError):
            info.total_count = 200  # type: ignore[misc]

    def test_has_more_with_next_url(self) -> None:
        """has_more should return True when next_url is set."""
        info = PaginationInfo(next_url="https://api.example.com/next")
        assert info.has_more is True

    def test_has_more_with_remaining_records(self) -> None:
        """has_more should return True when more records exist."""
        info = PaginationInfo(total_count=100, offset=0, limit=50)
        assert info.has_more is True

    def test_has_more_false_at_end(self) -> None:
        """has_more should return False at end of pagination."""
        info = PaginationInfo(total_count=100, offset=50, limit=50)
        assert info.has_more is False

    def test_has_more_false_when_unknown(self) -> None:
        """has_more should return False when total_count is unknown."""
        info = PaginationInfo(offset=50, limit=50)
        assert info.has_more is False

    def test_from_dict_with_complete_data(self) -> None:
        """from_dict should create instance from complete dict."""
        data: dict[str, Any] = {
            "total_count": 500,
            "offset": 100,
            "limit": 50,
            "next_url": "https://api.example.com/page2",
        }
        info = PaginationInfo.from_dict(data)

        assert info.total_count == 500
        assert info.offset == 100
        assert info.limit == 50
        assert info.next_url == "https://api.example.com/page2"

    def test_from_dict_with_partial_data(self) -> None:
        """from_dict should handle partial data with defaults."""
        data: dict[str, Any] = {"total_count": 200}
        info = PaginationInfo.from_dict(data)

        assert info.total_count == 200
        assert info.offset == 0
        assert info.limit == 0
        assert info.next_url is None

    def test_from_dict_with_empty_dict(self) -> None:
        """from_dict should handle empty dict with all defaults."""
        info = PaginationInfo.from_dict({})

        assert info.total_count is None
        assert info.offset == 0
        assert info.limit == 0
        assert info.next_url is None

    def test_from_dict_ignores_invalid_types(self) -> None:
        """from_dict should use defaults for invalid types."""
        data: dict[str, Any] = {
            "total_count": "not_an_int",
            "offset": None,
            "limit": 3.14,
            "next_url": 123,
        }
        info = PaginationInfo.from_dict(data)

        assert info.total_count is None
        assert info.offset == 0
        assert info.limit == 0
        assert info.next_url is None

    def test_equality(self) -> None:
        """PaginationInfo instances with same values should be equal."""
        info1 = PaginationInfo(total_count=100, offset=0, limit=50)
        info2 = PaginationInfo(total_count=100, offset=0, limit=50)
        assert info1 == info2

    def test_hashable(self) -> None:
        """PaginationInfo should be hashable (usable in sets/dicts)."""
        info1 = PaginationInfo(total_count=100)
        info2 = PaginationInfo(total_count=100)
        info_set = {info1, info2}
        assert len(info_set) == 1


class TestPortsModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_are_importable(self) -> None:
        """All items in __all__ should be importable from the module."""
        from bioetl.domain.ports import parsing

        for name in parsing.__all__:
            assert hasattr(parsing, name), f"{name} not found in module"

    def test_exports_from_package_init(self) -> None:
        """All exports should be available from package init."""
        from bioetl.domain import ports

        assert hasattr(ports, "RawPayload")
        assert hasattr(ports, "RawRecordDict")
        assert hasattr(ports, "RawRecordList")
        assert hasattr(ports, "ResponseParserPortABC")
        assert hasattr(ports, "PaginationInfo")

"""DQ report serializer: JSON, YAML, HTML format conversion without I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast  # Any: needed for _serialize_value recursive return

import orjson

from bioetl.domain.behavior._dq_serializer_html import (
    DQSerializerHtmlCompatibilityMixin,
)
from bioetl.domain.behavior._dq_serializer_html import (
    generate_html_report as generate_html_report,
)
from bioetl.domain.behavior._dq_serializer_yaml import format_yaml_scalar
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQReportFormat,
    GoldDQReport,
    SilverDQReport,
)


def to_dict(obj: object) -> JsonDict:
    """Convert an object to a dictionary suitable for serialization.

    Handles dataclasses, enums, datetimes, and collection types.

    Args:
        obj: Object to convert.

    Returns:
        Dictionary representation of the object.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        return cast(JsonDict, _serialize_value(obj))
    if isinstance(obj, Mapping):
        return cast(JsonDict, _serialize_value(obj))
    return {"value": _serialize_value(obj)}


def _serialize_dataclass(
    value: Any,  # Any: guarded by _is_dataclass_instance() before calling fields()
) -> JsonDict:
    """Serialize a dataclass instance to dict."""
    return {
        field.name: _serialize_value(getattr(value, field.name))
        for field in fields(value)
    }


def _serialize_collection(
    value: Mapping[str, object]
    | list[object]
    | tuple[object, ...]
    | set[object]
    | frozenset[object],
) -> JsonDict | list[object]:  # output mirrors heterogeneous input structure
    """Serialize dict/list/tuple/set recursively."""
    if isinstance(value, Mapping):
        return _serialize_mapping(value)
    if isinstance(value, (set, frozenset)):
        return _serialize_set(value)
    return _serialize_sequence(value)


def _serialize_mapping(value: Mapping[str, object]) -> JsonDict:
    """Serialize a mapping recursively."""
    return {key: _serialize_value(item) for key, item in value.items()}


def _serialize_set(value: set[object] | frozenset[object]) -> list[object]:
    """Serialize an unordered collection in deterministic representation order."""
    return [_serialize_value(item) for item in sorted(value, key=repr)]


def _serialize_sequence(
    value: list[object] | tuple[object, ...],
) -> list[object]:
    """Serialize an ordered collection recursively."""
    return [_serialize_value(item) for item in value]


def _is_dataclass_instance(value: object) -> bool:
    """Check if value is a dataclass instance (not a class)."""
    return is_dataclass(value) and not isinstance(value, type)


def _serialize_value(
    value: Any,  # Any: recursive serializer handles heterogeneous types
) -> Any:  # Any: recursive serializer handles heterogeneous types
    """Serialize a value with dataclass/enum/datetime/collection support."""
    if _is_dataclass_instance(value):
        return _serialize_dataclass(value)
    if isinstance(value, (Mapping, list, tuple, set, frozenset)):
        return _serialize_collection(value)
    return _serialize_scalar(value)


def _serialize_scalar(value: Any) -> Any:  # Any: heterogeneous scalar passthrough
    """Serialize supported scalar values and pass through JSON-native scalars."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


class DQReportSerializer(DQSerializerHtmlCompatibilityMixin):
    """Serializer for DQ reports to various formats.

    Converts DQ report value objects to JSON, YAML, or HTML strings.
    """

    def serialize(
        self,
        report: BronzeDQReport | SilverDQReport | GoldDQReport,
        format: DQReportFormat = DQReportFormat.JSON,
    ) -> str:
        """Serialize DQ report to string.

        Args:
            report: DQ report to serialize.
            format: Output format (json, yaml, html).

        Returns:
            Serialized report string.
        """
        if format == DQReportFormat.JSON:
            return self._to_json(report)
        elif format == DQReportFormat.YAML:
            return self._to_yaml(report)
        elif format == DQReportFormat.HTML:
            return self._to_html(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def to_dict(
        self, report: BronzeDQReport | SilverDQReport | GoldDQReport
    ) -> JsonDict:
        """Convert report to dictionary.

        Args:
            report: Report.

        Returns:
            Dictionary representation.
        """
        return to_dict(report)

    def _to_json(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to JSON with pretty formatting."""
        data = to_dict(report)
        result: str = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        ).decode("utf-8")
        return result

    def _to_yaml(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to deterministic YAML without infrastructure dependencies."""
        return self._dict_to_yaml(to_dict(report))

    def _to_html(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to HTML report with styling."""
        return self._generate_html(to_dict(report), report)

    def _dict_to_yaml(self, data: JsonDict, indent: int = 0) -> str:
        """Simple YAML serialization with explicit empty collections."""
        lines = []
        prefix = "  " * indent

        for key, value in data.items():
            lines.extend(self._yaml_entry(key, value, prefix, indent))

        return "\n".join(lines)

    def _yaml_entry(
        self,
        key: str,
        value: object,
        prefix: str,
        indent: int,
    ) -> list[str]:
        """Convert a single key-value pair to YAML lines."""
        if isinstance(value, dict):
            if not value:
                return [f"{prefix}{key}: {{}}"]
            return [f"{prefix}{key}:", self._dict_to_yaml(value, indent + 1)]
        if isinstance(value, list):
            if not value:
                return [f"{prefix}{key}: []"]
            return [f"{prefix}{key}:", *self._yaml_list(value, prefix, indent)]
        return [f"{prefix}{key}: {self._yaml_value(value)}"]

    def _yaml_list(
        self,
        items: list[object],
        prefix: str,
        indent: int,
    ) -> list[str]:
        """Convert a list to YAML lines."""
        lines = []
        for item in items:
            lines.extend(self._yaml_list_item(item, prefix, indent))
        return lines

    def _yaml_list_item(
        self,
        item: object,
        prefix: str,
        indent: int,
    ) -> list[str]:
        """Convert one list item to YAML lines."""
        if isinstance(item, dict):
            return self._yaml_dict_list_item(item, prefix, indent)
        if isinstance(item, list):
            return self._yaml_nested_list_item(item, prefix, indent)
        return [f"{prefix}  - {self._yaml_value(item)}"]

    def _yaml_dict_list_item(
        self,
        item: dict[object, object],
        prefix: str,
        indent: int,
    ) -> list[str]:
        """Convert a mapping list item to YAML lines."""
        if not item:
            return [f"{prefix}  - {{}}"]
        return [f"{prefix}  -", self._dict_to_yaml(cast(JsonDict, item), indent + 2)]

    def _yaml_nested_list_item(
        self,
        item: list[object],
        prefix: str,
        indent: int,
    ) -> list[str]:
        """Convert a nested-list item to YAML lines."""
        if not item:
            return [f"{prefix}  - []"]
        return [
            f"{prefix}  -",
            *self._yaml_list(item, prefix + "  ", indent + 1),
        ]

    def _yaml_value(self, value: object) -> str:
        """Format a single YAML scalar deterministically."""
        return format_yaml_scalar(value)

    def _quote_yaml_string(self, value: str) -> str:
        """Quote a YAML string when plain-scalar syntax would be ambiguous."""
        return self._yaml_value(value)


__all__ = ["DQReportSerializer"]

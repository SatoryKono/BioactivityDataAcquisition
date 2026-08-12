"""DQ report serializer: JSON, YAML, HTML format conversion without I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast  # Any: needed for _serialize_value recursive return

import orjson
import yaml

from bioetl.domain.behavior._dq_serializer_html import (
    format_detail_value,
    generate_html_report,
    render_check_details_html,
    render_checks_html,
    render_thresholds_html,
    status_color_class,
)
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
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [_serialize_value(item) for item in sorted(value, key=repr)]
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
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (Mapping, list, tuple, set, frozenset)):
        return _serialize_collection(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


class DQReportSerializer:
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
        """Serialize to YAML via safe_dump for correct scalar quoting."""
        data = to_dict(report)
        dumped = yaml.safe_dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=True,
        )
        return cast(str, dumped).rstrip("\n")

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
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{prefix}  - {{}}")
                else:
                    lines.append(f"{prefix}  -")
                    lines.append(self._dict_to_yaml(item, indent + 2))
            elif isinstance(item, list):
                if not item:
                    lines.append(f"{prefix}  - []")
                else:
                    lines.append(f"{prefix}  -")
                    lines.extend(self._yaml_list(item, prefix + "  ", indent + 1))
            else:
                lines.append(f"{prefix}  - {self._yaml_value(item)}")
        return lines

    def _yaml_value(self, value: object) -> str:
        """Format a single value for YAML using safe_dump scalar form."""
        dumped = yaml.safe_dump(
            value,
            default_flow_style=True,
            allow_unicode=True,
        )
        return cast(str, dumped).strip()

    def _quote_yaml_string(self, value: str) -> str:
        """Quote YAML string with full escaping via safe_dump."""
        return self._yaml_value(value)

    def _generate_html(
        self,
        data: JsonDict,
        report: BronzeDQReport | SilverDQReport | GoldDQReport,
    ) -> str:
        """Generate HTML report."""
        del report
        return generate_html_report(data)

    def _status_color(self, status: str) -> str:
        """Get CSS class for status."""
        return status_color_class(status)

    def _render_checks_html(self, checks: JsonDict) -> str:
        """Render checks as HTML."""
        return render_checks_html(checks)

    def _render_check_details(self, data: JsonDict) -> str:
        """Render check details as HTML table."""
        return render_check_details_html(data)

    def _format_detail_value(self, value: object) -> str:
        """Format a detail value for HTML display."""
        return format_detail_value(value)

    def _render_thresholds_html(self, thresholds: JsonDict) -> str:
        """Render thresholds card as HTML."""
        return render_thresholds_html(thresholds)


__all__ = ["DQReportSerializer"]

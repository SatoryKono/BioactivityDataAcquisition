"""DQ report serializer.

Provides serialization of DQ reports to JSON, YAML, and HTML formats.
This is a domain service that handles format conversion without I/O.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, cast

import orjson

from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQReportFormat,
    GoldDQReport,
    SilverDQReport,
)


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
    ) -> dict[str, Any]:
        """Convert report to dictionary.

        Args:
            report: DQ report to convert.

        Returns:
            Dictionary representation of report.
        """
        return cast(dict[str, Any], self._dataclass_to_dict(report))

    def _to_json(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to JSON with pretty formatting."""
        data = self._dataclass_to_dict(report)
        return orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        ).decode("utf-8")

    def _to_yaml(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to YAML format.

        Uses simple YAML serialization without external dependencies.
        For production use, consider using ruamel.yaml or PyYAML.
        """
        data = self._dataclass_to_dict(report)
        return self._dict_to_yaml(data)

    def _to_html(self, report: BronzeDQReport | SilverDQReport | GoldDQReport) -> str:
        """Serialize to HTML report.

        Generates a simple HTML report with styling.
        """
        data = self._dataclass_to_dict(report)
        return self._generate_html(data, report)

    def _dataclass_to_dict(self, obj: Any) -> Any:
        """Recursively convert dataclass to dict with enum/datetime handling."""
        if is_dataclass(obj) and not isinstance(obj, type):
            return {k: self._dataclass_to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, tuple):
            return [self._dataclass_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._dataclass_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._dataclass_to_dict(item) for item in obj]
        else:
            return obj

    def _dict_to_yaml(self, data: dict[str, Any], indent: int = 0) -> str:
        """Simple YAML serialization without external dependencies."""
        lines = []
        prefix = "  " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.append(self._dict_to_yaml(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {self._yaml_value(item)}")
            else:
                lines.append(f"{prefix}{key}: {self._yaml_value(value)}")

        return "\n".join(lines)

    def _yaml_value(self, value: Any) -> str:
        """Format a single value for YAML."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            if "\n" in value or ":" in value or "#" in value:
                return f'"{value}"'
            return value
        else:
            return str(value)

    def _generate_html(
        self,
        data: dict[str, Any],
        report: BronzeDQReport | SilverDQReport | GoldDQReport,  # noqa: ARG002
    ) -> str:
        """Generate HTML report."""
        layer = data.get("layer", "unknown").upper()
        status = data.get("summary", {}).get("overall_status", "unknown")

        checks_html = self._render_checks_html(data.get("checks", {}))

        summary = data.get("summary", {})
        thresholds = data.get("thresholds", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DQ Report - {layer} Layer</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .report-header h1 {{ margin: 0 0 10px 0; }}
        .report-header .meta {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            font-size: 14px;
            opacity: 0.9;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 14px;
        }}
        .status-pass {{ background: #28a745; color: white; }}
        .status-warning {{ background: #ffc107; color: #333; }}
        .status-fail {{ background: #dc3545; color: white; }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        .summary-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .summary-item .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .summary-item .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .check-item {{
            padding: 15px;
            border-left: 4px solid #ddd;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 0 8px 8px 0;
        }}
        .check-item.pass {{ border-left-color: #28a745; }}
        .check-item.warn {{ border-left-color: #ffc107; }}
        .check-item.fail {{ border-left-color: #dc3545; }}
        .check-item h3 {{
            margin: 0 0 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .check-details {{
            font-size: 14px;
            color: #666;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{layer} Layer DQ Report</h1>
        <div style="margin: 15px 0;">
            <span class="status-badge status-{status}">{status}</span>
        </div>
        <div class="meta">
            <span><strong>Pipeline:</strong> {data.get("pipeline", "N/A")}</span>
            <span><strong>Run ID:</strong> {data.get("run_id", "N/A")}</span>
            <span><strong>Timestamp:</strong> {data.get("timestamp", "N/A")}</span>
        </div>
    </div>

    <div class="card">
        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="value">{summary.get("total_checks", 0)}</div>
                <div class="label">Total Checks</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #28a745;">{summary.get("passed", 0)}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #ffc107;">{summary.get("warnings", 0)}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #dc3545;">{summary.get("failed", 0)}</div>
                <div class="label">Failed</div>
            </div>
        </div>
    </div>

    {self._render_thresholds_html(thresholds) if thresholds else ""}

    <div class="card">
        <h2>Check Results</h2>
        {checks_html}
    </div>

    <div class="card">
        <h2>Raw Report Data</h2>
        <pre>{orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode()}</pre>
    </div>
</body>
</html>"""
        return html

    def _status_color(self, status: str) -> str:
        """Get CSS class for status."""
        status_lower = status.lower()
        if status_lower in ("pass", "passed"):
            return "pass"
        elif status_lower in ("warn", "warning"):
            return "warning"
        else:
            return "fail"

    def _render_checks_html(self, checks: dict[str, Any]) -> str:
        """Render checks as HTML."""
        if not checks:
            return "<p>No checks performed.</p>"

        html_parts = []
        for check_name, check_data in checks.items():
            if isinstance(check_data, dict):
                status = check_data.get("status", "pass")
                status_class = self._status_color(status)

                html_parts.append(f"""
                <div class="check-item {status_class}">
                    <h3>
                        <span>{check_name.replace("_", " ").title()}</span>
                        <span class="status-badge status-{status_class}">{status}</span>
                    </h3>
                    <div class="check-details">
                        {self._render_check_details(check_data)}
                    </div>
                </div>
                """)
            else:
                html_parts.append(f"""
                <div class="check-item pass">
                    <h3>{check_name.replace("_", " ").title()}</h3>
                    <div class="check-details">{check_data}</div>
                </div>
                """)

        return "\n".join(html_parts)

    def _render_check_details(self, data: dict[str, Any]) -> str:
        """Render check details as HTML table."""
        rows = []
        for key, value in data.items():
            if key == "status":
                continue
            if isinstance(value, dict):
                value_str = f"<pre>{orjson.dumps(value, option=orjson.OPT_INDENT_2).decode()}</pre>"
            elif isinstance(value, (list, tuple)):
                value_str = ", ".join(str(v) for v in value) if value else "[]"
            else:
                value_str = str(value)
            rows.append(
                f"<tr><td><strong>{key.replace('_', ' ').title()}</strong></td><td>{value_str}</td></tr>"
            )

        if not rows:
            return "<p>No details available.</p>"

        return f"<table>{''.join(rows)}</table>"

    def _render_thresholds_html(self, thresholds: dict[str, Any]) -> str:
        """Render thresholds card as HTML."""
        if not thresholds:
            return ""

        status = thresholds.get("threshold_status", "pass")
        status_class = self._status_color(status)

        return f"""
    <div class="card">
        <h2>DQ Thresholds</h2>
        <div class="check-item {status_class}">
            <table>
                <tr><td><strong>Soft Fail Threshold</strong></td><td>{thresholds.get("soft_fail_threshold", "N/A")}</td></tr>
                <tr><td><strong>Hard Fail Threshold</strong></td><td>{thresholds.get("hard_fail_threshold", "N/A")}</td></tr>
                <tr><td><strong>Current Error Rate</strong></td><td>{thresholds.get("current_error_rate", "N/A")}</td></tr>
                <tr><td><strong>Status</strong></td><td><span class="status-badge status-{status_class}">{status}</span></td></tr>
            </table>
        </div>
    </div>
        """


__all__ = ["DQReportSerializer"]

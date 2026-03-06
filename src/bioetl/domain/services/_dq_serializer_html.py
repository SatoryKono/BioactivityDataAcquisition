"""HTML rendering helpers for DQ report serialization."""

from __future__ import annotations

import orjson

from bioetl.domain.types import JsonDict

__all__ = [
    "format_detail_value",
    "generate_html_report",
    "render_check_details_html",
    "render_checks_html",
    "render_thresholds_html",
    "status_color_class",
]


def status_color_class(status: str) -> str:
    """Get CSS class for status."""
    status_lower = status.lower()
    if status_lower in ("pass", "passed"):
        return "pass"
    if status_lower in ("warn", "warning"):
        return "warning"
    return "fail"


def render_checks_html(checks: JsonDict) -> str:
    """Render checks as HTML."""
    if not checks:
        return "<p>No checks performed.</p>"

    html_parts: list[str] = []
    for check_name, check_data in checks.items():
        if isinstance(check_data, dict):
            status = check_data.get("status", "pass")
            status_class = status_color_class(str(status))
            html_parts.append(
                f"""
                <div class="check-item {status_class}">
                    <h3>
                        <span>{check_name.replace("_", " ").title()}</span>
                        <span class="status-badge status-{status_class}">{status}</span>
                    </h3>
                    <div class="check-details">
                        {render_check_details_html(check_data)}
                    </div>
                </div>
                """
            )
        else:
            html_parts.append(
                f"""
                <div class="check-item pass">
                    <h3>{check_name.replace("_", " ").title()}</h3>
                    <div class="check-details">{check_data}</div>
                </div>
                """
            )
    return "\n".join(html_parts)


def render_check_details_html(data: JsonDict) -> str:
    """Render check details as HTML table."""
    rows: list[str] = []
    for key, value in data.items():
        if key == "status":
            continue
        value_str = format_detail_value(value)
        rows.append(
            f"<tr><td><strong>{key.replace('_', ' ').title()}</strong></td><td>{value_str}</td></tr>"
        )

    if not rows:
        return "<p>No details available.</p>"

    return f"<table>{''.join(rows)}</table>"


def format_detail_value(value: object) -> str:
    """Format a detail value for HTML display."""
    if isinstance(value, dict):
        return f"<pre>{orjson.dumps(value, option=orjson.OPT_INDENT_2).decode()}</pre>"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "[]"
    return str(value)


def render_thresholds_html(thresholds: JsonDict) -> str:
    """Render thresholds card as HTML."""
    if not thresholds:
        return ""
    status = str(thresholds.get("threshold_status", "pass"))
    status_class = status_color_class(status)
    soft = thresholds.get("soft_fail_threshold")
    hard = thresholds.get("hard_fail_threshold")
    rate = thresholds.get("current_error_rate")
    return f"""
    <div class="card">
        <h2>DQ Thresholds</h2>
        <div class="check-item {status_class}">
            <table>
                <tr><td><strong>Soft Fail Threshold</strong></td><td>{soft if soft is not None else "—"}</td></tr>
                <tr><td><strong>Hard Fail Threshold</strong></td><td>{hard if hard is not None else "—"}</td></tr>
                <tr><td><strong>Current Error Rate</strong></td><td>{rate if rate is not None else "—"}</td></tr>
                <tr>
                    <td><strong>Status</strong></td>
                    <td><span class="status-badge status-{status_class}">{status}</span></td>
                </tr>
            </table>
        </div>
    </div>
        """


def generate_html_report(data: JsonDict) -> str:
    """Generate HTML report from serialized DQ payload.

    Returns:
        Complete HTML document string for the DQ report.
    """
    layer = str(data.get("layer", "unknown")).upper()
    status = str(data.get("summary", {}).get("overall_status", "unknown"))
    checks_html = render_checks_html(data.get("checks", {}))
    summary = data.get("summary", {})
    thresholds = data.get("thresholds", {})

    return f"""<!DOCTYPE html>
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
            <span><strong>Pipeline:</strong> {data.get("pipeline") or "—"}</span>
            <span><strong>Run ID:</strong> {data.get("run_id") or "—"}</span>
            <span><strong>Timestamp:</strong> {data.get("timestamp") or "—"}</span>
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

    {render_thresholds_html(thresholds) if thresholds else ""}

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

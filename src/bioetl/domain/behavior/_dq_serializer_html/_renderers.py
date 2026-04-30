"""HTML rendering helpers for DQ report sections."""

from __future__ import annotations

import orjson

from bioetl.domain.types import JsonDict

from ._styles import _REPORT_STYLES


def status_color_class(status: str) -> str:
    """Get CSS class for status.

    Args:
        status: Status string (e.g., 'pass', 'warn', 'fail').
    """
    status_lower = status.lower()
    if status_lower in ("pass", "passed"):
        return "pass"
    if status_lower in ("warn", "warning"):
        return "warning"
    return "fail"


def render_checks_html(checks: JsonDict) -> str:
    """Render checks as HTML.

    Args:
        checks: Mapping of check names to check result dicts or scalar values.
    """
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
    """Render check details as HTML table.

    Args:
        data: Check result dict containing key-value detail fields;
            the 'status' key is excluded from the rendered rows.
    """
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
    """Format a detail value for HTML display.

    Args:
        value: Value to format; dicts are pretty-printed as JSON, lists/tuples
            are joined as comma-separated strings, all others are converted via str().
    """
    if isinstance(value, dict):
        return f"<pre>{orjson.dumps(value, option=orjson.OPT_INDENT_2).decode()}</pre>"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "[]"
    return str(value)


def render_thresholds_html(thresholds: JsonDict) -> str:
    """Render thresholds card as HTML.

    Args:
        thresholds: Dict containing threshold data with optional keys
            'threshold_status', 'soft_fail_threshold', 'hard_fail_threshold',
            and 'current_error_rate'.
    """
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


def _render_report_header(*, layer: str, status: str, data: JsonDict) -> str:
    return f"""
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
    """


def _render_summary_card(summary: JsonDict) -> str:
    return f"""
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
    """


def _render_check_results_card(checks_html: str) -> str:
    return f"""
    <div class="card">
        <h2>Check Results</h2>
        {checks_html}
    </div>
    """


def _render_raw_data_card(data: JsonDict) -> str:
    payload = orjson.dumps(
        data,
        option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
    ).decode()
    return f"""
    <div class="card">
        <h2>Raw Report Data</h2>
        <pre>{payload}</pre>
    </div>
    """


__all__ = [
    "_REPORT_STYLES",
    "_render_check_results_card",
    "_render_raw_data_card",
    "_render_report_header",
    "_render_summary_card",
    "format_detail_value",
    "render_check_details_html",
    "render_checks_html",
    "render_thresholds_html",
    "status_color_class",
]

"""HTML rendering helpers for DQ report sections."""

from __future__ import annotations

from html import escape

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
        # Stylesheet uses .check-item.warn (not .warning).
        return "warn"
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
                        <span>{escape(str(check_name).replace("_", " ").title())}</span>
                        <span class="status-badge status-{escape(status_class)}">{escape(str(status))}</span>
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
                    <h3>{escape(str(check_name).replace("_", " ").title())}</h3>
                    <div class="check-details">{escape(str(check_data))}</div>
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
            "<tr><td><strong>"
            f"{escape(str(key).replace('_', ' ').title())}"
            f"</strong></td><td>{value_str}</td></tr>"
        )

    if not rows:
        return "<p>No details available.</p>"

    return f"<table>{''.join(rows)}</table>"


def _format_dict_detail(value: dict[str, object] | dict[object, object]) -> str:
    try:
        payload = orjson.dumps(
            value,
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
        ).decode()
    except (TypeError, orjson.JSONEncodeError):
        return f"<pre>{escape(str(value))}</pre>"
    return f"<pre>{escape(payload)}</pre>"


def _format_sequence_detail(value: list[object] | tuple[object, ...]) -> str:
    if not value:
        return "[]"
    parts = [escape(str(item)) for item in value]
    return ", ".join(parts)


def format_detail_value(value: object) -> str:
    """Format a detail value for HTML display.

    Args:
        value: Value to format; dicts are pretty-printed as JSON, lists/tuples
            are joined as comma-separated strings, all others are converted via str().
    """
    if isinstance(value, dict):
        return _format_dict_detail(value)
    if isinstance(value, (list, tuple)):
        return _format_sequence_detail(value)
    return escape(str(value))


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
    soft_text = escape(str(soft)) if soft is not None else "—"
    hard_text = escape(str(hard)) if hard is not None else "—"
    rate_text = escape(str(rate)) if rate is not None else "—"
    return f"""
    <div class="card">
        <h2>DQ Thresholds</h2>
        <div class="check-item {status_class}">
            <table>
                <tr><td><strong>Soft Fail Threshold</strong></td><td>{soft_text}</td></tr>
                <tr><td><strong>Hard Fail Threshold</strong></td><td>{hard_text}</td></tr>
                <tr><td><strong>Current Error Rate</strong></td><td>{rate_text}</td></tr>
                <tr>
                    <td><strong>Status</strong></td>
                    <td><span class="status-badge status-{status_class}">{escape(status)}</span></td>
                </tr>
            </table>
        </div>
        </div>
        """


def _render_report_header(*, layer: str, status: str, data: JsonDict) -> str:
    status_class = status_color_class(status)
    return f"""
    <div class="report-header">
        <h1>{escape(layer)} Layer DQ Report</h1>
        <div style="margin: 15px 0;">
            <span class="status-badge status-{status_class}">{escape(status)}</span>
        </div>
        <div class="meta">
            <span><strong>Pipeline:</strong> {escape(str(data.get("pipeline") or "—"))}</span>
            <span><strong>Run ID:</strong> {escape(str(data.get("run_id") or "—"))}</span>
            <span><strong>Timestamp:</strong> {escape(str(data.get("timestamp") or "—"))}</span>
        </div>
    </div>
    """


def _render_summary_card(summary: JsonDict) -> str:
    return f"""
    <div class="card">
        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="value">{escape(str(summary.get("total_checks", 0)))}</div>
                <div class="label">Total Checks</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #28a745;">{escape(str(summary.get("passed", 0)))}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #ffc107;">{escape(str(summary.get("warnings", 0)))}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #dc3545;">{escape(str(summary.get("failed", 0)))}</div>
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
    try:
        payload = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS,
        ).decode()
    except (TypeError, orjson.JSONEncodeError):
        # Fail-soft: keep report rendering alive for Decimal/set/non-str keys.
        payload = orjson.dumps(
            {
                "error": "raw_data_not_serializable",
                "keys": sorted(map(str, data.keys())),
            },
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        ).decode()
    return f"""
    <div class="card">
        <h2>Raw Report Data</h2>
        <pre>{escape(payload)}</pre>
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

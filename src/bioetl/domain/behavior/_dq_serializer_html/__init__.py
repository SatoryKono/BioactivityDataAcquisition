"""HTML rendering helpers for DQ report serialization."""

from __future__ import annotations

from html import escape

from bioetl.domain.types import JsonDict

from ._renderers import (
    _render_check_results_card,
    _render_raw_data_card,
    _render_report_header,
    _render_summary_card,
    format_detail_value,
    render_check_details_html,
    render_checks_html,
    render_thresholds_html,
    status_color_class,
)
from ._styles import _REPORT_STYLES

__all__ = [
    "format_detail_value",
    "generate_html_report",
    "render_check_details_html",
    "render_checks_html",
    "render_thresholds_html",
    "status_color_class",
]


def generate_html_report(data: JsonDict) -> str:
    """Generate HTML report from serialized DQ payload.

    Args:
        data: Serialized DQ report payload containing keys such as 'layer',
            'summary', 'checks', and optionally 'thresholds'.

    Returns:
        Complete HTML document string for the DQ report.
    """
    summary_raw = data.get("summary")
    summary = summary_raw if isinstance(summary_raw, dict) else {}
    checks_raw = data.get("checks")
    checks = checks_raw if isinstance(checks_raw, dict) else {}
    thresholds_raw = data.get("thresholds")
    thresholds = thresholds_raw if isinstance(thresholds_raw, dict) else {}
    layer = str(data.get("layer", "unknown")).upper()
    status = str(summary.get("overall_status", "unknown"))
    checks_html = render_checks_html(checks)
    thresholds_html = render_thresholds_html(thresholds) if thresholds else ""
    header_html = _render_report_header(layer=layer, status=status, data=data)
    summary_html = _render_summary_card(summary)
    checks_card_html = _render_check_results_card(checks_html)
    raw_data_html = _render_raw_data_card(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DQ Report - {escape(layer)} Layer</title>
    <style>
{_REPORT_STYLES}
    </style>
</head>
<body>
{header_html}
{summary_html}
{thresholds_html}
{checks_card_html}
{raw_data_html}
</body>
</html>"""

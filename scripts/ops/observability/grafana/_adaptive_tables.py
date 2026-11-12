"""Keep native wide tables and a readable transposed view on narrow panels."""

from __future__ import annotations

import html
import re

ADAPTIVE_TABLE_TYPE = "bioetl-selectorshell-panel"


def _navigation_labels(content: str) -> str:
    for title, short in (
        ("1. Run Explorer", "1. Runs"),
        ("2. Replay Readiness", "2. Replay"),
        ("3. Run Overview", "3. Overview"),
        ("4. Data Quality", "4. Quality"),
        ("5. Incident Workspace", "5. Incidents"),
    ):
        content = re.sub(
            rf"(<(?:a|span)\b[^>]*)(>)({re.escape(title)})(</(?:a|span)>)",
            lambda match, title=title, short=short: (
                match[1]
                + f' aria-label="{html.escape(title)}"'
                + match[2]
                + short
                + match[4]
            ),
            content,
        )
    return content


def apply_adaptive_tables(payload: dict) -> None:
    """Change presentation only; retain every query, field, link and mapping."""
    uid = payload.get("uid")
    modes = {
        "bioetl-run-explorer-v1": {3010: "runs"},
        "bioetl-overview-v2": {
            99: "record",
            9603: "record",
            9002: "rows",
            2005: "rows",
            22005: "rows",
        },
        "bioetl-dq-v2": {9400: "record", 9406: "record", 9403: "rows"},
        "bioetl-control-plane-v1": {9416: "rows"},
        "bioetl-incident-v1": {2010: "rows", 2005: "rows", 22005: "rows"},
    }.get(uid, {})
    panels = list(payload.get("panels", []))
    while panels:
        panel = panels.pop(0)
        panels.extend(panel.get("panels", []))
        if panel.get("id") == 1000:
            panel["options"]["content"] = _navigation_labels(
                panel["options"]["content"]
            )
        if uid == "bioetl-incident-v1" and panel.get("id") == 9400:
            panel["options"]["content"] = (
                '<div style="font-size:16px;line-height:1.2">'
                "CURRENT: ${workflow:text} / ${pipeline:text} / ${run_type:text}. "
                "GLOBAL tables: all pipelines; Run ID ignored. "
                "Suspects unverified; empty does not mean healthy.</div>"
            )
        if uid == "bioetl-incident-v1" and panel.get("id") == 2001:
            panel["options"]["content"] = (
                panel["options"]["content"]
                .replace(
                    "Rule triggered; cause not confirmed. Read the ranked suspect first. Fleet blockers and time-range charts are in Pipeline fleet and range on this page. PENDING has not fired. ",
                    "Suspects first; cause unverified. PENDING is not firing. Fleet blockers: Pipeline fleet and range. ",
                )
                .replace("Stage lag/backlog measurements", "Lag/backlog")
            )
        mode = modes.get(panel.get("id"))
        if mode is None:
            continue
        if panel.get("type") != "table":
            raise ValueError(
                f"Adaptive target must be a native table: {uid}:{panel['id']}"
            )
        panel["type"] = ADAPTIVE_TABLE_TYPE
        panel.setdefault("options", {})["viewMode"] = mode
        compact_fields = {
            2010: ["Severity", "Cause verification", "Signal", "Object"],
            2005: ["State", "Severity", "Alert", "Pipeline"],
            22005: ["State", "Severity", "Alert", "Pipeline"],
            9416: ["Parameter", "Priority", "Present", "Result", "Value"],
        }.get(panel["id"])
        if compact_fields:
            panel["options"]["compactFields"] = compact_fields
        description = panel.get("description", "")
        note = (
            " Below 1024 px viewport width, labels and values transpose into a "
            "compact record. Full details retain the complete values and run "
            "identity. Catalog pagination retains every returned run."
        )
        if note not in description:
            panel["description"] = description + note

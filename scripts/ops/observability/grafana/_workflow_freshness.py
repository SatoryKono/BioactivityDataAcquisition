"""Publication-age warning, independent of retained workflow health evidence."""

from __future__ import annotations

FRESH_SECONDS = 86400
VARIABLE = "workflow_evidence_freshness"
TITLE_SUFFIX = " · ${workflow_evidence_freshness} · threshold 24h"
NOT_VERIFIED = "Not verified"


def apply_workflow_freshness(payload: dict, row: dict, scope: str) -> None:
    """Expose age and unknown timestamps without inventing healthy zeroes."""
    universe = f"group by(workflow)(bioetl_workflow_scope_universe{{{scope}}})"
    published = "bioetl_workflow_scope_published_seconds"
    valid = f"({published} > 0 and {published} <= time())"
    scoped = f"({valid} and on(workflow) {universe})"
    age = f"(time() - {scoped})"
    missing = f"({universe} unless on(workflow) {valid})"
    stale = f"(max({age}) > {FRESH_SECONDS})"
    unknown = f"(count({missing}) > 0 or absent({universe}))"
    # One scalar label: missing coverage takes precedence over a within-threshold
    # assertion. Known stale rows remain visible even with incomplete coverage.
    state = (
        f'label_replace({stale}, "freshness", "STALE", "", "")'
        f' or on() label_replace({unknown}, "freshness", "{NOT_VERIFIED}", "", "")'
        f" or on() label_replace((max({age}) <= {FRESH_SECONDS}), "
        '"freshness", "Within threshold", "", "")'
    )
    query = f"query_result({state})"
    variables = payload.setdefault("templating", {}).setdefault("list", [])
    variables[:] = [v for v in variables if v.get("name") != VARIABLE]
    variables.append(
        {
            "name": VARIABLE,
            "type": "query",
            "hide": 2,
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "definition": query,
            "query": {"query": query, "refId": "StandardVariableQuery"},
            "regex": '/freshness="([^"]+)"/',
            "refresh": 2,
            "skipUrlSync": True,
            "multi": False,
            "includeAll": False,
            "options": [],
            "current": {"text": NOT_VERIFIED, "value": NOT_VERIFIED},
        }
    )
    row["title"] += TITLE_SUFFIX
    panel = row["panels"][0]
    panel["title"] += TITLE_SUFFIX
    panel["description"] += (
        " Publication age is measured at query evaluation. Display threshold: 24h "
        "(86400 seconds); STALE means age > threshold, not workflow failure. "
        "Within threshold does not prove health. Missing/invalid publication time "
        f"is {NOT_VERIFIED}. The heading uses the oldest scoped publication; any "
        "known stale row takes precedence over missing coverage. Retention and "
        "health status are unchanged. Refresh the dashboard to re-evaluate."
    )
    panel["targets"][1]["expr"] = f"{scoped} * 1000"
    for ref, expr in (
        ("C", age),
        ("D", f"{universe} * {FRESH_SECONDS}"),
        ("E", f"{age} > bool {FRESH_SECONDS}"),
    ):
        panel["targets"].append(
            {"refId": ref, "instant": True, "format": "table", "expr": expr}
        )
    fields = {
        "Value #C": "Publication age",
        "Value #D": "Freshness threshold",
        "Value #E": "Freshness",
    }
    panel["transformations"][1]["options"]["include"]["names"].extend(fields)
    panel["transformations"][2]["options"]["renameByName"].update(fields)
    overrides = panel["fieldConfig"]["overrides"]
    for name in ("Publication age", "Freshness threshold"):
        overrides.append(
            {
                "matcher": {"id": "byName", "options": name},
                "properties": [
                    {"id": "unit", "value": "s"},
                    {"id": "noValue", "value": NOT_VERIFIED},
                ],
            }
        )
    overrides.append(
        {
            "matcher": {"id": "byName", "options": "Freshness"},
            "properties": [
                {"id": "noValue", "value": NOT_VERIFIED},
                {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "0": {"text": "Within threshold"},
                                "1": {"text": "STALE", "color": "orange"},
                            },
                        }
                    ],
                },
            ],
        }
    )
    overrides.append(
        {
            "matcher": {"id": "byName", "options": "Published at"},
            "properties": [
                {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"},
                {"id": "noValue", "value": NOT_VERIFIED},
            ],
        }
    )

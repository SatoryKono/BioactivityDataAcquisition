"""Compare Grafana v2 conversion semantics against the provisioned v1 source."""

from __future__ import annotations

import copy


def _field_config(value: dict) -> dict:
    result = copy.deepcopy(value)
    defaults = result.setdefault("defaults", {})
    result.setdefault("overrides", [])
    # Grafana's schema omits empty optional lists; populated lists remain exact.
    for key in ("links", "mappings"):
        if defaults.get(key) == []:
            defaults.pop(key)
    thresholds = [defaults.get("thresholds", {})]
    thresholds.extend(
        p.get("value", {})
        for o in result["overrides"]
        for p in o.get("properties", [])
        if p.get("id") == "thresholds"
    )
    for threshold in thresholds:
        steps = threshold.get("steps", [])
        if steps and steps[0].get("value") is None:
            steps[0].pop("value", None)
    return result


def _links(values: list[dict]) -> list[dict]:
    # v2 PanelLink retains these three fields; dashboard-link metadata such as
    # icon/tooltip is not part of PanelLink. Keep functional destinations exact.
    return [
        {
            "title": v.get("title", ""),
            "url": v.get("url", ""),
            "targetBlank": v.get("targetBlank", False),
        }
        for v in values
    ]


def _query(target: dict, datasource: dict) -> dict:
    selected = target.get("datasource", datasource)
    return {
        "kind": "PanelQuery",
        "spec": {
            "refId": target.get("refId", ""),
            "hidden": target.get("hide", False),
            "query": {
                "kind": "DataQuery",
                "group": selected.get("type", ""),
                "version": "v0",
                "datasource": {"name": selected.get("uid", "")},
                "spec": {
                    k: v
                    for k, v in target.items()
                    if k not in {"datasource", "refId", "hide"}
                },
            },
        },
    }


def _grid(panels: list[dict], offset: int = 0) -> dict:
    return {
        "kind": "GridLayout",
        "spec": {
            "items": [
                {
                    "kind": "GridLayoutItem",
                    "spec": {
                        "element": {
                            "kind": "ElementReference",
                            "name": f"panel-{p['id']}",
                        },
                        "height": p["gridPos"]["h"],
                        "width": p["gridPos"]["w"],
                        "x": p["gridPos"]["x"],
                        "y": p["gridPos"]["y"] - offset,
                    },
                }
                for p in sorted(
                    panels, key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"])
                )
            ]
        },
    }


def _layout(panels: list[dict]) -> dict:
    if not any(p.get("type") == "row" for p in panels):
        return _grid(panels)
    rows, current = [], []
    row = None

    def flush() -> None:
        if row is None:
            if current:
                rows.append(
                    {
                        "kind": "RowsLayoutRow",
                        "spec": {
                            "title": "",
                            "collapse": False,
                            "hideHeader": True,
                            "layout": _grid(current),
                        },
                    }
                )
        else:
            rows.append(
                {
                    "kind": "RowsLayoutRow",
                    "spec": {
                        "title": row.get("title", ""),
                        "collapse": row.get("collapsed", False),
                        "layout": _grid(current, row["gridPos"]["y"] + 1),
                    },
                }
            )

    for panel in panels:
        if panel.get("type") == "row":
            flush()
            row, current = panel, list(panel.get("panels", []))
        else:
            current.append(panel)
    flush()
    return {"kind": "RowsLayout", "spec": {"rows": rows}}


def semantic_errors(source: dict, converted: dict) -> list[str]:
    """Fail closed on lost panels, queries, transformations, layout or variables."""
    try:
        return _semantic_errors(source, converted)
    except (KeyError, TypeError, AttributeError, ValueError):
        return ["unsupported or malformed v2 conversion semantics"]


def _panel_data(panel: dict) -> dict:
    return {
        "queries": [
            _query(t, panel.get("datasource", {})) for t in panel.get("targets", [])
        ],
        "transformations": [
            {
                "kind": "Transformation",
                "group": t["id"],
                "spec": {k: v for k, v in t.items() if k != "id"},
            }
            for t in panel.get("transformations", [])
        ],
        "queryOptions": {
            k: panel[k]
            for k in (
                "maxDataPoints",
                "interval",
                "timeFrom",
                "timeShift",
                "hideTimeOverride",
                "cacheTimeout",
                "queryCachingTTL",
            )
            if k in panel
        },
    }


def _panel_errors(panel: dict, element: dict) -> list[str]:
    errors = []
    actual = element.get("spec", {})
    viz = actual.get("vizConfig", {})
    data = actual.get("data", {})
    if element.get("kind") != "Panel" or any(
        actual.get(k, default) != panel.get(k, default)
        for k, default in (("id", None), ("title", ""), ("description", ""))
    ):
        errors.append(f"v2 panel identity differs: {panel['id']}")
    if _links(actual.get("links", [])) != _links(panel.get("links", [])):
        errors.append(f"v2 panel links differ: {panel['id']}")
    actual_viz = copy.deepcopy(viz.get("spec", {}))
    actual_viz["fieldConfig"] = _field_config(actual_viz.get("fieldConfig", {}))
    expected_viz = {
        "options": panel.get("options", {}),
        "fieldConfig": _field_config(panel.get("fieldConfig", {})),
    }
    if viz.get("group") != panel["type"] or actual_viz != expected_viz:
        errors.append(f"v2 panel visualization differs: {panel['id']}")
    if data.get("kind") != "QueryGroup" or data.get("spec") != _panel_data(panel):
        errors.append(f"v2 panel queries/transformations differ: {panel['id']}")
    return errors


def _variable_value(variable: dict, actual: dict, key: str) -> tuple:
    observed, expected = actual.get(key), variable[key]
    if key == "current" and isinstance(expected, dict):
        expected = {k: v for k, v in expected.items() if k != "selected"}
    if key == "options" and expected == [] and observed is None:
        observed = []
    if key == "query" and variable["type"] == "query":
        observed = actual["query"]["spec"]
    return observed, expected


def _variable_errors(variable: dict, value: dict) -> list[str]:
    errors = []
    actual = value["spec"]
    keys = (
        "name",
        "label",
        "description",
        "query",
        "regex",
        "multi",
        "includeAll",
        "allValue",
        "skipUrlSync",
        "options",
        "current",
    )
    for key in keys:
        if key in variable:
            observed, expected = _variable_value(variable, actual, key)
            if observed != expected:
                errors.append(f"v2 variable {key} differs: {variable['name']}")
    if variable["type"] == "query":
        query, datasource = actual["query"], variable.get("datasource", {})
        if query.get("group") != datasource.get("type") or query.get(
            "datasource", {}
        ).get("name") != datasource.get("uid"):
            errors.append(f"v2 variable datasource differs: {variable['name']}")
    return errors


def _variables_errors(source: dict, converted: dict) -> list[str]:
    errors = []
    variables = source.get("templating", {}).get("list", [])
    actual = converted.get("variables", [])
    if [v.get("spec", {}).get("name") for v in actual] != [
        v["name"] for v in variables
    ]:
        errors.append("v2 variable inventory differs from source")
    for variable, value in zip(variables, actual, strict=False):
        errors.extend(_variable_errors(variable, value))
    return errors


def _semantic_errors(source: dict, converted: dict) -> list[str]:
    errors = []
    panels = list(source.get("panels", []))
    flattened = []
    for panel in panels:
        flattened.extend(
            panel.get("panels", []) if panel.get("type") == "row" else [panel]
        )
    elements = converted["elements"]
    if set(elements) != {f"panel-{p['id']}" for p in flattened}:
        errors.append("v2 panel inventory differs from source")
    for panel in flattened:
        errors.extend(_panel_errors(panel, elements.get(f"panel-{panel['id']}", {})))
    if converted["layout"] != _layout(panels):
        errors.append("v2 layout differs from source")
    errors.extend(_variables_errors(source, converted))
    return errors

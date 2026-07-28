"""W4: reduce cognitive complexity in audit_live_grafana_panels.py."""
from __future__ import annotations

from pathlib import Path

TARGET = Path("scripts/ops/observability/grafana/audit_live_grafana_panels.py")

HELPERS = r'''

def _panel_specs_from_targets(
    *,
    dashboard_uid: str,
    panel_id: int,
    title: str,
    panel: dict[str, Any],
) -> list[PanelAuditSpec]:
    specs: list[PanelAuditSpec] = []
    for target in cast(list[dict[str, Any]], panel.get("targets", [])):
        ref_id = _target_ref_id(target)
        url = target.get("url")
        if isinstance(url, str) and url:
            specs.append(
                PanelAuditSpec(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    source_kind="http",
                    semantic_kind=cast(
                        Literal[
                            "freshness",
                            "http_endpoint",
                            "http_records",
                            "http_summary",
                            "http_table",
                        ],
                        _infer_http_semantic_kind(url),
                    ),
                    target_ref_id=ref_id,
                    required=False,
                )
            )
            continue
        expr = target.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            continue
        datasource_name = _datasource_name(panel, target).lower()
        kind = "loki" if "loki" in datasource_name else "prometheus"
        semantic = "loki_query" if kind == "loki" else "prometheus_query"
        specs.append(
            PanelAuditSpec(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                title=title,
                source_kind=kind,  # type: ignore[arg-type]
                semantic_kind=semantic,  # type: ignore[arg-type]
                target_ref_id=ref_id,
                required=False,
            )
        )
    return specs


def _panel_specs_from_links(
    *,
    dashboard_uid: str,
    panel_id: int,
    title: str,
    panel: dict[str, Any],
) -> list[PanelAuditSpec]:
    specs: list[PanelAuditSpec] = []
    for link in cast(list[dict[str, Any]], panel.get("links", [])):
        link_url = str(link.get("url") or "")
        if "exploretraces-app" not in link_url and "var-ds=tempo" not in link_url:
            continue
        specs.append(
            PanelAuditSpec(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                title=f"{title} :: {link.get('title') or 'Tempo handoff'}",
                source_kind="tempo",
                semantic_kind="tempo_handoff",
                target_ref_id=str(link.get("title") or "tempo"),
                required=False,
            )
        )
    return specs


def _classify_prometheus_vector(result: object) -> tuple[str, str]:
    if not isinstance(result, list):
        return ("invalid_shape", "Prometheus vector result must be a list")
    if not result:
        return ("empty_result", "Prometheus vector returned no samples")
    values: list[float] = []
    for item in result:
        if not isinstance(item, dict):
            return ("invalid_shape", "Prometheus vector sample must be an object")
        sample = item.get("value")
        if not isinstance(sample, list) or len(sample) != 2:
            return ("invalid_shape", "Prometheus vector sample missing value pair")
        try:
            values.append(float(sample[1]))
        except (TypeError, ValueError):
            return (
                "invalid_shape",
                "Prometheus vector sample value is not numeric",
            )
    if all(abs(value) <= 1e-12 for value in values):
        return ("zero_result", "Prometheus vector returned only zero values")
    return ("nonzero_result", "Prometheus vector returned non-zero values")


def _classify_prometheus_scalar(result: object) -> tuple[str, str]:
    if not isinstance(result, list) or len(result) != 2:
        return ("invalid_shape", "Prometheus scalar result missing value pair")
    try:
        value = float(result[1])
    except (TypeError, ValueError):
        return ("invalid_shape", "Prometheus scalar value is not numeric")
    if abs(value) <= 1e-12:
        return ("zero_result", "Prometheus scalar returned zero")
    return ("nonzero_result", "Prometheus scalar returned non-zero value")


'''

OLD_DISCOVER = '''def _discover_dashboard_panel_specs() -> tuple[PanelAuditSpec, ...]:
    specs: list[PanelAuditSpec] = []
    for path in sorted(_DASHBOARD_DIR.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        dashboard_uid = str(dashboard.get("uid") or path.stem)
        for panel in _iter_panels(
            cast(list[dict[str, Any]], dashboard.get("panels", []))
        ):
            panel_id = panel.get("id")
            if not isinstance(panel_id, int):
                continue
            title = str(panel.get("title") or f"panel-{panel_id}")
            for target in cast(list[dict[str, Any]], panel.get("targets", [])):
                ref_id = _target_ref_id(target)
                url = target.get("url")
                if isinstance(url, str) and url:
                    specs.append(
                        PanelAuditSpec(
                            dashboard_uid=dashboard_uid,
                            panel_id=panel_id,
                            title=title,
                            source_kind="http",
                            semantic_kind=cast(
                                Literal[
                                    "freshness",
                                    "http_endpoint",
                                    "http_records",
                                    "http_summary",
                                    "http_table",
                                ],
                                _infer_http_semantic_kind(url),
                            ),
                            target_ref_id=ref_id,
                            required=False,
                        )
                    )
                    continue
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                datasource_name = _datasource_name(panel, target).lower()
                if "loki" in datasource_name:
                    specs.append(
                        PanelAuditSpec(
                            dashboard_uid=dashboard_uid,
                            panel_id=panel_id,
                            title=title,
                            source_kind="loki",
                            semantic_kind="loki_query",
                            target_ref_id=ref_id,
                            required=False,
                        )
                    )
                else:
                    specs.append(
                        PanelAuditSpec(
                            dashboard_uid=dashboard_uid,
                            panel_id=panel_id,
                            title=title,
                            source_kind="prometheus",
                            semantic_kind="prometheus_query",
                            target_ref_id=ref_id,
                            required=False,
                        )
                    )
            for link in cast(list[dict[str, Any]], panel.get("links", [])):
                link_url = str(link.get("url") or "")
                if (
                    "exploretraces-app" not in link_url
                    and "var-ds=tempo" not in link_url
                ):
                    continue
                specs.append(
                    PanelAuditSpec(
                        dashboard_uid=dashboard_uid,
                        panel_id=panel_id,
                        title=f"{title} :: {link.get('title') or 'Tempo handoff'}",
                        source_kind="tempo",
                        semantic_kind="tempo_handoff",
                        target_ref_id=str(link.get("title") or "tempo"),
                        required=False,
                    )
                )
    return tuple(specs)
'''

NEW_DISCOVER = '''def _discover_dashboard_panel_specs() -> tuple[PanelAuditSpec, ...]:
    specs: list[PanelAuditSpec] = []
    for path in sorted(_DASHBOARD_DIR.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        dashboard_uid = str(dashboard.get("uid") or path.stem)
        for panel in _iter_panels(
            cast(list[dict[str, Any]], dashboard.get("panels", []))
        ):
            panel_id = panel.get("id")
            if not isinstance(panel_id, int):
                continue
            title = str(panel.get("title") or f"panel-{panel_id}")
            specs.extend(
                _panel_specs_from_targets(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    panel=panel,
                )
            )
            specs.extend(
                _panel_specs_from_links(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    panel=panel,
                )
            )
    return tuple(specs)
'''

OLD_PROM = '''def _classify_prometheus_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "Prometheus payload is not a JSON object")
    if payload.get("status") != "success":
        return ("query_error", f"Prometheus status={payload.get('status')!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return ("invalid_shape", "Prometheus payload missing data object")
    result = data.get("result")
    result_type = data.get("resultType")
    if result_type == "vector":
        if not isinstance(result, list):
            return ("invalid_shape", "Prometheus vector result must be a list")
        if not result:
            return ("empty_result", "Prometheus vector returned no samples")
        values: list[float] = []
        for item in result:
            if not isinstance(item, dict):
                return ("invalid_shape", "Prometheus vector sample must be an object")
            sample = item.get("value")
            if not isinstance(sample, list) or len(sample) != 2:
                return ("invalid_shape", "Prometheus vector sample missing value pair")
            try:
                values.append(float(sample[1]))
            except (TypeError, ValueError):
                return (
                    "invalid_shape",
                    "Prometheus vector sample value is not numeric",
                )
        if all(abs(value) <= 1e-12 for value in values):
            return ("zero_result", "Prometheus vector returned only zero values")
        return ("nonzero_result", "Prometheus vector returned non-zero values")
    if result_type == "scalar":
        if not isinstance(result, list) or len(result) != 2:
            return ("invalid_shape", "Prometheus scalar result missing value pair")
        try:
            value = float(result[1])
        except (TypeError, ValueError):
            return ("invalid_shape", "Prometheus scalar value is not numeric")
        if abs(value) <= 1e-12:
            return ("zero_result", "Prometheus scalar returned zero")
        return ("nonzero_result", "Prometheus scalar returned non-zero value")
    return ("invalid_shape", f"Unsupported Prometheus resultType={result_type!r}")
'''

NEW_PROM = '''def _classify_prometheus_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "Prometheus payload is not a JSON object")
    if payload.get("status") != "success":
        return ("query_error", f"Prometheus status={payload.get('status')!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return ("invalid_shape", "Prometheus payload missing data object")
    result = data.get("result")
    result_type = data.get("resultType")
    if result_type == "vector":
        return _classify_prometheus_vector(result)
    if result_type == "scalar":
        return _classify_prometheus_scalar(result)
    return ("invalid_shape", f"Unsupported Prometheus resultType={result_type!r}")
'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "_panel_specs_from_targets(" not in text:
        text = text.replace(
            "def _discover_dashboard_panel_specs()",
            HELPERS + "def _discover_dashboard_panel_specs()",
            1,
        )
        print("inserted helpers")
    if OLD_DISCOVER in text:
        text = text.replace(OLD_DISCOVER, NEW_DISCOVER, 1)
        print("replaced discover")
    elif "for target in cast" not in text[text.find("def _discover_dashboard_panel_specs") : text.find("def _discover_dashboard_panel_specs") + 900]:
        print("discover already simplified")
    else:
        raise SystemExit("discover block missing")
    if OLD_PROM in text:
        text = text.replace(OLD_PROM, NEW_PROM, 1)
        print("replaced prom classify")
    elif "_classify_prometheus_vector(" in text:
        print("prom classify already simplified")
    else:
        raise SystemExit("prom classify missing")
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", TARGET)


if __name__ == "__main__":
    main()

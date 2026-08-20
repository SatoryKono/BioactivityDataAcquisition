"""Typed target analysis and report helpers for observability inventory."""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _as_repo_relative,
    _import_from_nodes,
    _iter_text_files,
    _load_declared_metric_definitions,
    _normalize_mapping_lists,
    _scan_canonical_metric_mentions,
    _scan_registered_metric_names,
)
from scripts.engineering.qa.observability_metric_inventory_shared import (
    _CANONICAL_METRIC_RE,
    _DOC_SCAN_ROOTS,
    _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS,
    _IGNORED_DOC_METRIC_NAMES,
    _PANEL_CONTRACT_INVENTORY,
    _POLICY_ALIAS_CATALOG,
    _PROMETHEUS_FAMILY_SUFFIXES,
    _REPO_ROOT,
    _RULE_SCAN_ROOT,
    _TEXT_SUFFIXES,
)


_COVERAGE_CLASSES_PATH = Path("configs/quality/observability_coverage_classes.yaml")
_PROMETHEUS_BUILTIN_METRIC_RE = re.compile(r"\b(?:ALERTS|ALERTS_FOR_STATE)\b")
_coverage_class_map: dict[str, str] = {}
_empty_state_map: dict[str, str] = {}


def _load_coverage_policy(repo_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    import yaml

    path = repo_root / _COVERAGE_CLASSES_PATH
    if not path.is_file():
        return {}, {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    classes = (
        payload.get("metric_coverage_classes") if isinstance(payload, dict) else {}
    )
    empty = payload.get("empty_state_by_class") if isinstance(payload, dict) else {}
    class_map = {
        str(key): str(value)
        for key, value in (classes or {}).items()
        if str(value)
        in {
            "required_current",
            "required_when_active",
            "event_optional",
            "historical_only",
            "deprecated",
        }
    }
    empty_map = {
        str(key): str(value)
        for key, value in (empty or {}).items()
        if str(value) in {"valid_empty", "coverage_gap", "not_applicable"}
    }
    return class_map, empty_map


def _coverage_for_tokens(
    tokens: list[str],
    class_map: dict[str, str],
    empty_map: dict[str, str],
) -> tuple[str | None, str | None]:
    for token in tokens:
        klass = class_map.get(token)
        if klass:
            return klass, empty_map.get(klass)
    return None, None


def _coerce_int(value: object, *, default: int = -1) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _iter_dashboard_panels(payload: dict[str, object]) -> list[dict[str, object]]:
    panels: list[dict[str, object]] = []
    raw_panels = payload.get("panels", [])
    if not isinstance(raw_panels, list):
        return panels
    for raw_panel in raw_panels:
        if not isinstance(raw_panel, dict):
            continue
        panels.append(raw_panel)
        panels.extend(_iter_dashboard_panels(raw_panel))
    return panels


def _field_config_link_candidates(field_config: object) -> list[object]:
    if not isinstance(field_config, dict):
        return []
    candidates: list[object] = []
    defaults = field_config.get("defaults", {})
    if isinstance(defaults, dict):
        candidates.extend(defaults.get("links", []))
    for override in field_config.get("overrides", []):
        if not isinstance(override, dict):
            continue
        for prop in override.get("properties", []):
            if isinstance(prop, dict) and prop.get("id") == "links":
                candidates.extend(prop.get("value", []))
    return candidates


def _runbook_urls_from_link_candidates(candidates: list[object]) -> list[str]:
    urls: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        url = str(candidate.get("url", ""))
        if "runbook" in url.lower():
            urls.add(url)
    return sorted(urls)


def _panel_runbook_urls(panel: dict[str, object]) -> list[str]:
    """Return deterministic runbook links from panel and field data links."""
    raw_links = panel.get("links", [])
    candidates: list[object] = list(raw_links) if isinstance(raw_links, list) else []
    candidates.extend(_field_config_link_candidates(panel.get("fieldConfig", {})))
    return _runbook_urls_from_link_candidates(candidates)


def _target_kind(*, datasource_type: str, target: dict[str, object]) -> str:
    """Classify one dashboard target without parsing HTTP URLs as PromQL."""
    normalized = datasource_type.lower()
    url = target.get("url")
    if isinstance(url, str) and url.startswith(("/ops/", "/health/")):
        return "http"
    if normalized == "loki":
        return "loki"
    if normalized == "tempo":
        return "tempo"
    if normalized in {"prometheus", "promql"} or target.get("expr") is not None:
        return "promql"
    return "unknown"


def _canonical_datasource_type(raw: str) -> str:
    """Resolve Grafana datasource names to their shipped plugin types."""
    return {
        "Quarantine Explorer": "yesoreyeram-infinity-datasource",
        "BioETL Ops HTTP": "yesoreyeram-infinity-datasource",
        "Prometheus": "prometheus",
        "Loki": "loki",
        "Tempo": "tempo",
    }.get(raw, raw)


def _target_query_tokens(kind: str, query: str) -> list[str]:
    """Extract stable, source-specific tokens for documentation parity."""
    if kind == "http":
        from urllib.parse import parse_qsl, urlsplit

        parsed = urlsplit(query)
        return [parsed.path, *(key for key, _value in parse_qsl(parsed.query))]
    if kind == "promql":
        tokens = set(_CANONICAL_METRIC_RE.findall(query))
        tokens.update(_PROMETHEUS_BUILTIN_METRIC_RE.findall(query))
        return sorted(tokens)
    if kind == "loki":
        return sorted(
            set(re.findall(r"\b(?:job|pipeline|level|event|logger)\b", query))
        )
    if kind == "tempo":
        return sorted(
            set(re.findall(r"\b(?:trace_id|span|resource|duration)\b", query))
        )
    return []


def _panel_contract(
    *,
    dashboard_uid: str,
    panel: dict[str, object],
    target: dict[str, object],
    datasource_type: str,
) -> dict[str, object]:
    """Build one complete, deterministic dashboard target documentation row."""
    panel_id = _coerce_int(panel.get("id", -1))
    kind = _target_kind(datasource_type=datasource_type, target=target)
    query = str(target.get("url") or target.get("expr") or target.get("query") or "")
    description = str(panel.get("description", ""))
    field_config = panel.get("fieldConfig", {})
    defaults = (
        field_config.get("defaults", {}) if isinstance(field_config, dict) else {}
    )
    if not isinstance(defaults, dict):
        defaults = {}
    documentation_lower = (f"{description} {defaults.get('noValue', '')}").lower()
    thresholds = defaults.get("thresholds", {})
    threshold_steps = (
        thresholds.get("steps", []) if isinstance(thresholds, dict) else []
    )
    tokens = _target_query_tokens(kind, query)
    coverage_class, empty_state = _coverage_for_tokens(
        tokens, _coverage_class_map, _empty_state_map
    )
    if kind == "http":
        empty_state = empty_state or "valid_empty"
    return {
        "dashboard_uid": dashboard_uid,
        "panel_id": panel_id,
        "panel_title": str(panel.get("title", "")),
        "ref_id": str(target.get("refId", "")),
        "kind": kind,
        "datasource_type": _canonical_datasource_type(datasource_type),
        "query": query,
        "query_tokens": tokens,
        "coverage_class": coverage_class,
        "empty_state": empty_state,
        "formula": str(target.get("expr") or target.get("expression") or ""),
        "unit": str(defaults.get("unit", "")),
        "thresholds": threshold_steps if isinstance(threshold_steps, list) else [],
        "runbook_urls": _panel_runbook_urls(panel),
        "documents_valid_empty": any(
            token in documentation_lower
            for token in (
                "valid empty",
                "expected empty",
                "legitimate empty",
                "empty means",
                "empty-state",
                "detail is empty",
                "0 can mean no rejects",
                "zero-row",
                "zero row",
                "0 rows",
                "no matching",
            )
        ),
        "documents_backend_down": any(
            token in documentation_lower
            for token in (
                "backend down",
                "backend failure",
                "backend unavailable",
                "backend may be unavailable",
                "backend/query failure",
                "datasource failure",
                "datasource error",
                "datasource errors",
                "quarantine explorer responds",
                "quarantine explorer and pipeline",
                "after the api",
                "until the api",
            )
        ),
    }


def _catalog_policy_aliases(repo_root: Path) -> set[str]:
    """Read the independent published policy-alias table."""
    text = (repo_root / _POLICY_ALIAS_CATALOG).read_text(encoding="utf-8")
    marker = "## Governed Policy Aliases"
    if marker not in text:
        return set()
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    return {
        match.group(1)
        for line in section.splitlines()
        if (match := re.match(r"^\| `([^`]+)` \|", line))
    }


def _panel_contract_document(
    typed_report: dict[str, object],
) -> dict[str, object]:
    """Build the committed full panel-contract documentation artifact."""
    return {
        "schema_version": 1,
        "source": "grafana/dashboards/*.json",
        "fields": [
            "datasource_type",
            "query_tokens",
            "coverage_class",
            "empty_state",
            "formula",
            "unit",
            "thresholds",
            "runbook_urls",
            "documents_valid_empty",
            "documents_backend_down",
        ],
        "target_counts": typed_report["typed_target_counts"],
        "targets": typed_report["typed_targets"],
    }


def _panel_contract_drift(
    repo_root: Path, typed_report: dict[str, object]
) -> list[str]:
    """Return a stable drift marker for the committed panel documentation."""
    path = repo_root / _PANEL_CONTRACT_INVENTORY
    if not path.is_file():
        return [f"missing:{_PANEL_CONTRACT_INVENTORY.as_posix()}"]
    try:
        expected = json.loads(
            path.read_text(encoding="utf-8")
        )  # NOSONAR - path confined
    except (OSError, json.JSONDecodeError):
        return [f"invalid:{_PANEL_CONTRACT_INVENTORY.as_posix()}"]
    if expected != _panel_contract_document(typed_report):
        return [f"mismatch:{_PANEL_CONTRACT_INVENTORY.as_posix()}"]
    return []


def write_panel_contract_inventory(
    repo_root: Path, typed_report: dict[str, object]
) -> Path:
    """Regenerate the deterministic full panel-contract documentation."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    path = resolve_output_path(_PANEL_CONTRACT_INVENTORY, root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(_panel_contract_document(typed_report), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return path


_RUN_ID_SELECTOR_RE = re.compile(r"\{[^{}]*\brun_id\s*(?:=|!=|=~|!~)")
_TYPED_RULE_RELATIVE_PATHS = (
    Path("grafana/prometheus-rules/bioetl_observability.yml"),
    Path("grafana/prometheus-rules/bioetl_control_plane_current_status.yml"),
)


def _datasource_type_text(raw: object, *, fallback: str = "") -> str:
    if isinstance(raw, dict):
        return str(raw.get("type", "")) or fallback
    if raw is None:
        return fallback
    return str(raw) or fallback


def _consume_prometheus_rule(
    rule: dict[str, object],
    *,
    relative_path: Path,
    recording_outputs: set[str],
    recording_inputs: set[str],
    direct_alert_inputs: set[str],
    run_id_selector_violations: list[str],
) -> None:
    expr = str(rule.get("expr", ""))
    metric_names = set(_CANONICAL_METRIC_RE.findall(expr))
    if rule.get("record"):
        recording_outputs.add(str(rule["record"]))
        recording_inputs.update(metric_names)
    elif rule.get("alert"):
        direct_alert_inputs.update(metric_names)
    if _RUN_ID_SELECTOR_RE.search(expr):
        run_id_selector_violations.append(
            f"{relative_path.as_posix()}::{rule.get('record') or rule.get('alert')}"
        )


def _scan_typed_prometheus_rules(
    repo_root: Path, yaml_module: Any
) -> tuple[set[str], set[str], set[str], list[str]]:
    recording_outputs: set[str] = set()
    recording_inputs: set[str] = set()
    direct_alert_inputs: set[str] = set()
    run_id_selector_violations: list[str] = []
    for relative_path in _TYPED_RULE_RELATIVE_PATHS:
        payload = yaml_module.safe_load(
            (repo_root / relative_path).read_text(encoding="utf-8")
        )
        for group in payload.get("groups", []):
            for rule in group.get("rules", []):
                if not isinstance(rule, dict):
                    continue
                _consume_prometheus_rule(
                    rule,
                    relative_path=relative_path,
                    recording_outputs=recording_outputs,
                    recording_inputs=recording_inputs,
                    direct_alert_inputs=direct_alert_inputs,
                    run_id_selector_violations=run_id_selector_violations,
                )
    return (
        recording_outputs,
        recording_inputs,
        direct_alert_inputs,
        run_id_selector_violations,
    )


def _http_target_row(
    contract: dict[str, object], target: dict[str, object]
) -> dict[str, object] | None:
    url = target.get("url")
    if not isinstance(url, str):
        return None
    if not (url.startswith("/ops/") or str(target.get("source", "")) == "url"):
        return None
    return contract | {
        "url": url,
        "uses_run_id_query_parameter": "run_id=" in url,
    }


def _consume_dashboard_target(
    target: dict[str, object],
    *,
    dashboard_path: Path,
    repo_root: Path,
    dashboard_uid: str,
    panel: dict[str, object],
    panel_id: int,
    panel_datasource_type: str,
    direct_dashboard_targets: set[str],
    typed_targets: list[dict[str, object]],
    http_targets: list[dict[str, object]],
    run_id_selector_violations: list[str],
) -> None:
    expr = str(target.get("expr", ""))
    direct_dashboard_targets.update(_CANONICAL_METRIC_RE.findall(expr))
    if _RUN_ID_SELECTOR_RE.search(expr):
        run_id_selector_violations.append(
            f"{dashboard_path.relative_to(repo_root).as_posix()}::panel={panel_id}"
        )
    target_datasource_type = _datasource_type_text(
        target.get("datasource", {}), fallback=panel_datasource_type
    )
    if not target_datasource_type:
        target_datasource_type = panel_datasource_type
    contract = _panel_contract(
        dashboard_uid=dashboard_uid,
        panel=panel,
        target=target,
        datasource_type=target_datasource_type,
    )
    if contract["query"]:
        typed_targets.append(contract)
    http_row = _http_target_row(contract, target)
    if http_row is not None:
        http_targets.append(http_row)


def _scan_typed_dashboard_targets(
    repo_root: Path,
) -> tuple[set[str], list[dict[str, object]], list[dict[str, object]], list[str]]:
    direct_dashboard_targets: set[str] = set()
    typed_targets: list[dict[str, object]] = []
    http_targets: list[dict[str, object]] = []
    run_id_selector_violations: list[str] = []
    dashboards_root = repo_root / "grafana" / "dashboards"
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        payload = json.loads(
            dashboard_path.read_text(encoding="utf-8")
        )  # NOSONAR - path confined
        dashboard_uid = str(payload.get("uid", dashboard_path.stem))
        for panel in _iter_dashboard_panels(payload):
            panel_id = _coerce_int(panel.get("id", -1))
            panel_datasource_type = _datasource_type_text(panel.get("datasource", {}))
            raw_targets = panel.get("targets", [])
            if not isinstance(raw_targets, list):
                continue
            for target in raw_targets:
                if not isinstance(target, dict):
                    continue
                _consume_dashboard_target(
                    target,
                    dashboard_path=dashboard_path,
                    repo_root=repo_root,
                    dashboard_uid=dashboard_uid,
                    panel=panel,
                    panel_id=panel_id,
                    panel_datasource_type=panel_datasource_type,
                    direct_dashboard_targets=direct_dashboard_targets,
                    typed_targets=typed_targets,
                    http_targets=http_targets,
                    run_id_selector_violations=run_id_selector_violations,
                )
    return (
        direct_dashboard_targets,
        typed_targets,
        http_targets,
        run_id_selector_violations,
    )


def _scan_documented_metrics_from_docs(repo_root: Path) -> set[str]:
    documented_metrics: set[str] = set()
    for scan_root in _DOC_SCAN_ROOTS:
        if scan_root == Path("grafana/dashboards"):
            continue
        path = repo_root / scan_root
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix not in _TEXT_SUFFIXES:
                continue
            try:
                documented_metrics.update(
                    _CANONICAL_METRIC_RE.findall(candidate.read_text(encoding="utf-8"))
                )
            except UnicodeDecodeError:
                continue
    return documented_metrics


def _typed_target_sort_key(row: dict[str, object]) -> tuple[str, int, str, str]:
    return (
        str(row["dashboard_uid"]),
        _coerce_int(row.get("panel_id", -1)),
        str(row["ref_id"]),
        str(row["kind"]),
    )


def _http_target_sort_key(row: dict[str, object]) -> tuple[str, int, str, str]:
    return (
        str(row["dashboard_uid"]),
        _coerce_int(row.get("panel_id", -1)),
        str(row["ref_id"]),
        str(row["url"]),
    )


def _coverage_class_violations(typed_targets: list[dict[str, object]]) -> list[str]:
    violations: list[str] = []
    for row in typed_targets:
        if row.get("kind") != "promql":
            continue
        if row.get("coverage_class"):
            continue
        violations.append(
            f"{row['dashboard_uid']}::panel={row['panel_id']}::ref={row['ref_id']}"
        )
    return violations


def _http_semantics_violations(typed_targets: list[dict[str, object]]) -> list[str]:
    return [
        f"{row['dashboard_uid']}::panel={row['panel_id']}"
        for row in typed_targets
        if row["kind"] == "http"
        and not (row["documents_valid_empty"] and row["documents_backend_down"])
    ]


def _build_typed_inventory_report(
    *,
    repo_root: Path,
    recording_outputs: set[str],
    recording_inputs: set[str],
    direct_alert_inputs: set[str],
    direct_dashboard_targets: set[str],
    documented_metrics: set[str],
    typed_targets: list[dict[str, object]],
    http_targets: list[dict[str, object]],
    run_id_selector_violations: list[str],
    declared_outputs: set[str],
    policy_aliases: set[str],
    catalog_aliases: set[str],
    registered_runtime_metrics: set[str],
) -> dict[str, object]:
    typed_targets.sort(key=_typed_target_sort_key)
    report: dict[str, object] = {
        "recording_rule_outputs": sorted(recording_outputs),
        "policy_alias_metrics": sorted(policy_aliases),
        "documented_metrics": sorted(documented_metrics),
        "direct_dashboard_targets": sorted(direct_dashboard_targets),
        "recording_rule_inputs": sorted(recording_inputs),
        "direct_alert_inputs": sorted(direct_alert_inputs),
        "typed_targets": typed_targets,
        "typed_target_counts": {
            kind: sum(1 for row in typed_targets if row["kind"] == kind)
            for kind in ("promql", "http", "loki", "tempo", "unknown")
        },
        "http_targets": sorted(http_targets, key=_http_target_sort_key),
        "recording_outputs_without_declaration": sorted(
            recording_outputs - declared_outputs
        ),
        "recording_declarations_without_output": sorted(
            declared_outputs - recording_outputs
        ),
        "policy_aliases_overlapping_outputs": sorted(
            policy_aliases & recording_outputs
        ),
        "policy_aliases_overlapping_runtime_metrics": sorted(
            policy_aliases & registered_runtime_metrics
        ),
        "policy_aliases_without_catalog": sorted(policy_aliases - catalog_aliases),
        "catalog_aliases_without_declaration": sorted(catalog_aliases - policy_aliases),
        "http_semantics_violations": sorted(
            set(_http_semantics_violations(typed_targets))
        ),
        "coverage_class_violations": sorted(
            set(_coverage_class_violations(typed_targets))
        ),
        "prometheus_run_id_selector_violations": sorted(run_id_selector_violations),
    }
    report["panel_contract_drift"] = _panel_contract_drift(repo_root, report)
    return report


def collect_typed_observability_inventory(repo_root: Path) -> dict[str, object]:
    """Collect deterministic rule/dashboard usage views without conflating sources."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - project runtime ships PyYAML
        raise RuntimeError(
            "PyYAML is required for typed observability inventory"
        ) from exc

    global _coverage_class_map, _empty_state_map
    _coverage_class_map, _empty_state_map = _load_coverage_policy(repo_root)
    declarations = _load_declared_metric_definitions(repo_root)
    (
        recording_outputs,
        recording_inputs,
        direct_alert_inputs,
        rule_run_id_violations,
    ) = _scan_typed_prometheus_rules(repo_root, yaml)
    (
        direct_dashboard_targets,
        typed_targets,
        http_targets,
        dashboard_run_id_violations,
    ) = _scan_typed_dashboard_targets(repo_root)
    documented_metrics = _scan_documented_metrics_from_docs(repo_root)
    return _build_typed_inventory_report(
        repo_root=repo_root,
        recording_outputs=recording_outputs,
        recording_inputs=recording_inputs,
        direct_alert_inputs=direct_alert_inputs,
        direct_dashboard_targets=direct_dashboard_targets,
        documented_metrics=documented_metrics,
        typed_targets=typed_targets,
        http_targets=http_targets,
        run_id_selector_violations=rule_run_id_violations + dashboard_run_id_violations,
        declared_outputs=declarations["recording_rule_metrics"],
        policy_aliases=declarations["policy_alias_metrics"],
        catalog_aliases=_catalog_policy_aliases(repo_root),
        registered_runtime_metrics=set(_scan_registered_metric_names(repo_root)),
    )


def _filter_declared_label_contract_metrics(
    unresolved_rows: list[str],
    declared_metric_names: set[str],
) -> list[str]:
    return [
        row
        for row in unresolved_rows
        if _drift_allowlist_token("runtime_label_contract_unresolved", row)
        not in declared_metric_names
    ]


def _looks_like_metric_family_name(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in _PROMETHEUS_FAMILY_SUFFIXES)


def _is_generated_prometheus_series(
    metric_name: str,
    registered_metrics: frozenset[str] | set[str],
) -> bool:
    histogram_suffixes = ("_bucket", "_sum", "_count")
    for suffix in histogram_suffixes:
        if metric_name.endswith(suffix):
            return metric_name[: -len(suffix)] in registered_metrics
    if metric_name.endswith("_created"):
        base = metric_name.removesuffix("_created")
        return base in registered_metrics or f"{base}_total" in registered_metrics
    return False


def _filter_documented_metric_mentions(
    mentions: dict[str, list[str]],
    *,
    registered_metrics: frozenset[str] | set[str],
) -> dict[str, list[str]]:
    filtered: dict[str, list[str]] = {}
    for metric_name, paths in mentions.items():
        if metric_name in _IGNORED_DOC_METRIC_NAMES:
            continue
        if metric_name.endswith("_"):
            continue
        if _is_generated_prometheus_series(metric_name, registered_metrics):
            continue
        if metric_name not in registered_metrics and not _looks_like_metric_family_name(
            metric_name
        ):
            continue
        filtered[metric_name] = paths
    return _normalize_mapping_lists(filtered)


def _scan_rule_metric_mentions(repo_root: Path) -> dict[str, list[str]]:
    try:
        import yaml
    except ImportError:
        return _scan_canonical_metric_mentions(
            _iter_text_files(repo_root / _RULE_SCAN_ROOT),
            repo_root,
        )

    mentions: dict[str, list[str]] = defaultdict(list)
    for path in _iter_text_files(repo_root / _RULE_SCAN_ROOT):
        try:
            payload = yaml.safe_load(
                path.read_text(encoding="utf-8")
            )  # NOSONAR - path confined
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(payload, dict):
            continue
        rel_path = _as_repo_relative(path, repo_root)
        groups = payload.get("groups", [])
        if not isinstance(groups, list):
            continue
        for metric_name in _extract_rule_metric_names(groups):
            mentions[metric_name].append(rel_path)
    return _normalize_mapping_lists(mentions)


def _extract_rule_metric_names(groups: list[object]) -> list[str]:
    metric_names: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        rules = group.get("rules", [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            expr = rule.get("expr")
            if isinstance(expr, str):
                metric_names.update(_CANONICAL_METRIC_RE.findall(expr))
    return sorted(metric_names)


def _drift_allowlist_token(key: str, value: str) -> str:
    """Normalize drift rows for allowlist comparison."""
    if key == "runtime_label_contract_unresolved":
        return value.split(" @ ", 1)[0]
    return value

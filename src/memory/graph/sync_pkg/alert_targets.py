"""Alert targeting helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Set

from memory.graph.sync_pkg._core_convert import _as_string_list
from memory.graph.sync_pkg._core_models import (
    AlertDashboardConfig,
    AlertRuleSettings,
    NodeKey,
)
from memory.graph.sync_pkg.dashboard_metrics import _extract_bioetl_metrics
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext

__all__ = [
    "_RUNTIME_DIMENSIONS",
    "_alert_dashboard_config",
    "_alert_dashboard_fallback_groups",
    "_alert_dashboard_fallbacks",
    "_alert_override_maps",
    "_alert_pipeline_kind_override",
    "_alert_rule_overrides",
    "_alert_rule_settings",
    "_alerts_config_section",
    "_all_contract_targets",
    "_all_pipeline_targets",
    "_configured_alert_rule",
    "_configured_dashboard_targets",
    "_contract_targets_for_alert",
    "_dashboard_target_keys",
    "_entity_alert_signal_detected",
    "_mapped_contract_targets",
    "_merged_alert_dashboard_targets",
    "_metric_dashboard_targets",
    "_pipeline_targets_for_alert",
    "_pipeline_targets_for_alert_mode",
    "_pipeline_targets_matching_kind",
    "_provider_alert_signal_detected",
    "_provider_targets_for_alert",
    "_provider_targets_requested",
    "_raw_alert_targets",
    "_runtime_dimensions",
    "_select_alert_dashboards",
    "_select_alert_targets",
    "_sorted_alert_targets",
    "_sorted_node_keys",
    "_sorted_unique_node_keys",
]


def _runtime_dimensions(*parts: str) -> set[str]:
    combined = " ".join(parts)
    dimensions = set()
    for dim in _RUNTIME_DIMENSIONS:
        if re.search(rf"\b{dim}\b", combined):
            dimensions.add(dim)
    return dimensions


_RUNTIME_DIMENSIONS = (
    "pipeline",
    "provider",
    "entity",
    "layer",
    "run_type",
    "stage",
    "table",
    "metric",
    "anomaly_type",
    "event_type",
    "store",
    "operation",
    "ref_type",
)


def _alert_rule_settings(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
    group_name: str,
) -> AlertRuleSettings:
    group_rule, alert_rule = _alert_rule_overrides(
        memory_mapping,
        alert_name=alert_name,
        group_name=group_name,
    )
    return AlertRuleSettings(
        pipeline_mode=str(
            alert_rule.get("pipelines", group_rule.get("pipelines", "auto"))
        ),
        pipeline_kind=str(
            alert_rule.get("pipeline_kind", group_rule.get("pipeline_kind", "any"))
        ),
        provider_mode=str(
            alert_rule.get("providers", group_rule.get("providers", "auto"))
        ),
        contract_mode=str(
            alert_rule.get("contracts", group_rule.get("contracts", "none"))
        ),
    )


def _alert_rule_overrides(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
    group_name: str,
) -> tuple[dict[str, object], dict[str, object]]:
    alerts_config = _alerts_config_section(memory_mapping)
    groups, rules = _alert_override_maps(alerts_config)
    group_rule = _as_mapping(groups.get(group_name)) if isinstance(groups, dict) else {}
    alert_rule = _as_mapping(rules.get(alert_name)) if isinstance(rules, dict) else {}
    return group_rule, alert_rule


def _alerts_config_section(memory_mapping: dict[str, object]) -> dict[str, object]:
    alerts_config = memory_mapping.get("alerts")
    return alerts_config if isinstance(alerts_config, dict) else {}


def _alert_override_maps(
    alerts_config: dict[str, object],
) -> tuple[object, object]:
    return alerts_config.get("groups"), alerts_config.get("rules")


def _pipeline_targets_for_alert(
    context: AlertTargetContext,
    *,
    pipeline_mode: str,
    pipeline_kind: str,
    normalized: str,
    dimensions: set[str],
) -> list[NodeKey]:
    pipeline_targets = _pipeline_targets_for_alert_mode(
        context, pipeline_mode, dimensions
    )
    effective_kind = _alert_pipeline_kind_override(
        pipeline_kind, normalized, dimensions
    )
    if effective_kind in {"entity", "composite"}:
        return _pipeline_targets_matching_kind(
            context, pipeline_targets, effective_kind
        )
    return pipeline_targets


def _pipeline_targets_for_alert_mode(
    context: AlertTargetContext,
    pipeline_mode: str,
    dimensions: set[str],
) -> list[NodeKey]:
    all_pipelines = _all_pipeline_targets(context)
    if pipeline_mode == "all":
        return all_pipelines
    if pipeline_mode == "entity":
        return _pipeline_targets_matching_kind(context, all_pipelines, "entity")
    if pipeline_mode == "composite":
        return _pipeline_targets_matching_kind(context, all_pipelines, "composite")
    if pipeline_mode == "auto" and "pipeline" in dimensions:
        return all_pipelines
    return []


def _all_pipeline_targets(context: AlertTargetContext) -> list[NodeKey]:
    return list(context.pipeline_nodes.values())


def _alert_pipeline_kind_override(
    pipeline_kind: str,
    normalized: str,
    dimensions: set[str],
) -> str:
    if pipeline_kind in {"entity", "composite"}:
        return pipeline_kind
    if _entity_alert_signal_detected(normalized, dimensions):
        return "entity"
    return pipeline_kind


def _entity_alert_signal_detected(normalized: str, dimensions: set[str]) -> bool:
    return "entity" in dimensions or any(
        marker in normalized
        for marker in (
            "bioetl_dq_",
            "bioetl_silver_",
            'stage="bronze"',
            "bioetl_data_freshness_seconds",
        )
    )


def _pipeline_targets_matching_kind(
    context: AlertTargetContext,
    pipeline_targets: Iterable[NodeKey],
    pipeline_kind: str,
) -> list[NodeKey]:
    return [
        node
        for node in pipeline_targets
        if context.snapshot.nodes[node].properties.get("pipeline_kind") == pipeline_kind
    ]


def _provider_targets_for_alert(
    context: AlertTargetContext,
    *,
    provider_mode: str,
    normalized: str,
    dimensions: set[str],
) -> list[NodeKey]:
    provider_targets_requested = _provider_targets_requested(
        provider_mode,
        normalized=normalized,
        dimensions=dimensions,
    )
    return context.provider_nodes if provider_targets_requested else []


def _provider_targets_requested(
    provider_mode: str,
    *,
    normalized: str,
    dimensions: set[str],
) -> bool:
    return provider_mode == "all" or (
        provider_mode == "auto"
        and _provider_alert_signal_detected(normalized, dimensions)
    )


def _provider_alert_signal_detected(normalized: str, dimensions: set[str]) -> bool:
    return (
        "provider" in dimensions
        or "provider_health" in normalized
        or "bioetl_health_check_" in normalized
    )


def _contract_targets_for_alert(
    context: AlertTargetContext,
    *,
    contract_mode: str,
    pipeline_targets: list[NodeKey],
) -> list[NodeKey]:
    if contract_mode == "all":
        return _all_contract_targets(context)
    if contract_mode != "mapped":
        return []
    return sorted(
        _mapped_contract_targets(context, pipeline_targets), key=lambda node: node.name
    )


def _all_contract_targets(context: AlertTargetContext) -> list[NodeKey]:
    return list(context.contract_nodes.values())


def _mapped_contract_targets(
    context: AlertTargetContext,
    pipeline_targets: Iterable[NodeKey],
) -> set[NodeKey]:
    pipeline_target_set = set(pipeline_targets)
    return {
        relation.target
        for relation in context.snapshot.relations.values()
        if relation.source in pipeline_target_set
        and relation.relation_type == "DEPENDS_ON"
        and relation.target.label == "contract_surface"
    }


def _select_alert_targets(
    context: AlertTargetContext,
    alert_name: str,
    group_name: str,
    expr: str,
    dimensions: set[str],
) -> AlertTargetSelection:
    pipeline_targets, provider_targets, contract_targets = _raw_alert_targets(
        context,
        alert_name=alert_name,
        group_name=group_name,
        expr=expr,
        dimensions=dimensions,
    )
    return _sorted_alert_targets(pipeline_targets, provider_targets, contract_targets)


def _sorted_unique_node_keys(nodes: Iterable[NodeKey]) -> tuple[NodeKey, ...]:
    return tuple(sorted(set(nodes), key=lambda node: node.name))


def _raw_alert_targets(
    context: AlertTargetContext,
    *,
    alert_name: str,
    group_name: str,
    expr: str,
    dimensions: set[str],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey]]:
    normalized = _normalized_alert_selector(group_name, expr)
    settings = _alert_rule_settings(
        context.memory_mapping,
        alert_name=alert_name,
        group_name=group_name,
    )
    pipeline_targets = _pipeline_targets_for_alert(
        context,
        pipeline_mode=settings.pipeline_mode,
        pipeline_kind=settings.pipeline_kind,
        normalized=normalized,
        dimensions=dimensions,
    )
    provider_targets = _provider_targets_for_alert(
        context,
        provider_mode=settings.provider_mode,
        normalized=normalized,
        dimensions=dimensions,
    )
    contract_targets = _contract_targets_for_alert(
        context,
        contract_mode=settings.contract_mode,
        pipeline_targets=pipeline_targets,
    )
    return pipeline_targets, provider_targets, contract_targets


def _sorted_alert_targets(
    pipeline_targets: list[NodeKey],
    provider_targets: list[NodeKey],
    contract_targets: list[NodeKey],
) -> AlertTargetSelection:
    return AlertTargetSelection(
        selected_pipelines=_sorted_unique_node_keys(pipeline_targets),
        selected_providers=_sorted_unique_node_keys(provider_targets),
        selected_contracts=_sorted_unique_node_keys(contract_targets),
    )


def _select_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    memory_mapping: dict[str, object],
) -> list[NodeKey]:
    config = _alert_dashboard_config(
        memory_mapping,
        alert_name=alert_name,
    )
    explicit_dashboards = _configured_dashboard_targets(
        config.alert_rule.get("dashboards")
    )
    common_dashboards = _configured_dashboard_targets(
        config.dashboard_fallbacks.get("common")
    )
    group_dashboards = _configured_dashboard_targets(
        config.fallback_groups.get(group_name)
    )
    metric_dashboards = _metric_dashboard_targets(expr, dashboard_metrics)
    return _merged_alert_dashboard_targets(
        explicit_dashboards=explicit_dashboards,
        metric_dashboards=metric_dashboards,
        group_dashboards=group_dashboards,
        common_dashboards=common_dashboards,
    )


def _merged_alert_dashboard_targets(
    *,
    explicit_dashboards: set[NodeKey],
    metric_dashboards: set[NodeKey],
    group_dashboards: set[NodeKey],
    common_dashboards: set[NodeKey],
) -> list[NodeKey]:
    selected = set(explicit_dashboards)
    selected.update(metric_dashboards)
    if not metric_dashboards:
        selected.update(group_dashboards)
    selected.update(common_dashboards)
    return _sorted_node_keys(selected)


def _sorted_node_keys(nodes: Iterable[NodeKey]) -> list[NodeKey]:
    return sorted(nodes, key=lambda node: node.name)


def _alert_dashboard_config(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
) -> AlertDashboardConfig:
    alerts_config = _alerts_config_section(memory_mapping)
    dashboard_fallbacks = _alert_dashboard_fallbacks(alerts_config)
    return AlertDashboardConfig(
        alert_rule=_configured_alert_rule(alerts_config, alert_name),
        dashboard_fallbacks=dashboard_fallbacks,
        fallback_groups=_alert_dashboard_fallback_groups(dashboard_fallbacks),
    )


def _configured_alert_rule(
    alerts_config: dict[str, object],
    alert_name: str,
) -> dict[str, object]:
    rules = alerts_config.get("rules")
    if not isinstance(rules, dict):
        return {}
    alert_rule = rules.get(alert_name)
    return alert_rule if isinstance(alert_rule, dict) else {}


def _alert_dashboard_fallbacks(
    alerts_config: dict[str, object],
) -> dict[str, object]:
    dashboard_fallbacks = alerts_config.get("dashboard_fallbacks")
    return dashboard_fallbacks if isinstance(dashboard_fallbacks, dict) else {}


def _alert_dashboard_fallback_groups(
    dashboard_fallbacks: dict[str, object],
) -> dict[str, object]:
    fallback_groups = dashboard_fallbacks.get("groups")
    return fallback_groups if isinstance(fallback_groups, dict) else {}


def _configured_dashboard_targets(values: object) -> set[NodeKey]:
    return _dashboard_target_keys(_as_string_list(values))


def _dashboard_target_keys(names: Iterable[str]) -> set[NodeKey]:
    return {NodeKey("dashboard_surface", name) for name in names}


def _metric_dashboard_targets(
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
) -> set[NodeKey]:
    metrics = _extract_bioetl_metrics(expr)
    return {
        dashboard
        for dashboard, dashboard_metric_names in dashboard_metrics.items()
        if metrics & dashboard_metric_names
    }

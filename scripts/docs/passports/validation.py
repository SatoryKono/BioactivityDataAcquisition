"""Fail-closed validation helpers for passport source projections."""

from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]

_MERGE_STRATEGIES = {"left_outer", "inner", "outer", "right_outer"}
_CONFLICT_RULES = {"seed_priority", "explicit_rules"}


def validate_composite_payload(
    payload: JsonObject,
    *,
    pipeline_output_keys: dict[str, set[str]] | None = None,
) -> list[JsonObject]:
    """Return deterministic diagnostics for executable composite invariants."""
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return [_error("COMPOSITE_CONFIG_MISSING")]
    seed = composite.get("seed")
    if not isinstance(seed, dict):
        return [_error("COMPOSITE_SEED_MISSING")]
    output_keys = _unique_strings(seed.get("output_keys"))
    diagnostics: list[JsonObject] = []
    if not output_keys:
        diagnostics.append(_error("COMPOSITE_SEED_OUTPUT_KEYS_EMPTY"))
    available_sources: set[str] = set()
    known_outputs = pipeline_output_keys or {}
    for role in ("dependencies", "enrichers"):
        for item in _mapping_items(composite.get(role)):
            join_keys = _unique_strings(item.get("join_keys"))
            if not join_keys:
                diagnostics.append(
                    _error("COMPOSITE_JOIN_KEYS_EMPTY", pipeline=item.get("pipeline"))
                )
                continue
            key_source = item.get("key_source")
            if isinstance(key_source, str):
                if key_source not in available_sources:
                    diagnostics.append(
                        _error(
                            "COMPOSITE_KEY_SOURCE_NOT_PRIOR",
                            pipeline=item.get("pipeline"),
                            key_source=key_source,
                        )
                    )
                valid_keys = known_outputs.get(key_source, set())
            else:
                valid_keys = set(output_keys)
            missing = sorted(set(join_keys) - valid_keys)
            if missing:
                diagnostics.append(
                    _error(
                        "COMPOSITE_JOIN_KEY_NOT_IN_SEED_OUTPUT",
                        pipeline=item.get("pipeline"),
                        keys=missing,
                    )
                )
            cardinality = item.get("cardinality")
            if cardinality not in (None, "one_to_one", "many_to_one"):
                diagnostics.append(
                    _error(
                        "COMPOSITE_CARDINALITY_UNSUPPORTED",
                        pipeline=item.get("pipeline"),
                        value=cardinality,
                    )
                )
            pipeline = item.get("pipeline")
            if isinstance(pipeline, str):
                available_sources.add(pipeline)
    merge = composite.get("merge")
    if not isinstance(merge, dict):
        diagnostics.append(_error("COMPOSITE_MERGE_MISSING"))
        return diagnostics
    if merge.get("strategy") not in _MERGE_STRATEGIES:
        diagnostics.append(
            _error("COMPOSITE_MERGE_STRATEGY_INVALID", value=merge.get("strategy"))
        )
    conflict_rule = merge.get("conflict_resolution")
    if conflict_rule not in _CONFLICT_RULES:
        diagnostics.append(
            _error("COMPOSITE_CONFLICT_RULE_INVALID", value=conflict_rule)
        )
    if conflict_rule == "explicit_rules":
        priorities = merge.get("field_priorities")
        if not isinstance(priorities, dict) or not priorities:
            diagnostics.append(_error("COMPOSITE_EXPLICIT_PRIORITIES_INCOMPLETE"))
        elif any(not _unique_strings(value) for value in priorities.values()):
            diagnostics.append(_error("COMPOSITE_EXPLICIT_PRIORITIES_INCOMPLETE"))
    aggregation = merge.get("aggregation")
    if aggregation not in (None, "none", "first", "collect_unique"):
        diagnostics.append(
            _error("COMPOSITE_AGGREGATION_UNSUPPORTED", value=aggregation)
        )
    return diagnostics


def workflow_mermaid(steps: list[JsonObject]) -> str:
    """Render a stable Mermaid DAG from already validated workflow steps."""
    lines = ["flowchart TD"]
    for step in sorted(steps, key=lambda item: str(item.get("step_id"))):
        step_id = str(step["step_id"])
        label = str(step.get("pipeline_name") or step.get("transform_name") or step_id)
        lines.append(f'  {step_id}["{label}"]')
    edges = sorted(
        (str(dependency), str(step["step_id"]))
        for step in steps
        for dependency in step.get("depends_on", [])
        if isinstance(dependency, str)
    )
    lines.extend(f"  {source} --> {target}" for source, target in edges)
    return "\n".join(lines) + "\n"


def _mapping_items(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _unique_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [item for item in value if isinstance(item, str) and item]
    return items if len(items) == len(set(items)) else []


def _error(code: str, **context: object) -> JsonObject:
    return {"code": code, "severity": "error", **context}

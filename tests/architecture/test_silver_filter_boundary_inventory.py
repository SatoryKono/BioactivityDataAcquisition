"""Architecture guardrails for Silver-vs-Gold filter boundary governance."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.observability.prometheus_metric_registries import (
    REGISTERED_PROMETHEUS_METRIC_NAMES,
)
from scripts.data_quality.inventory_silver_filters_migration import (
    CSV_OUT,
    JSON_OUT,
    MD_OUT,
    build_entity_plan,
    discover_entity_configs,
    write_csv,
    write_json,
    write_markdown,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs" / "quality" / "silver_filter_boundary_inventory.yaml"
ENTITY_CONFIG_ROOT = ROOT / "configs" / "entities"
COMPOSITE_CONFIG_ROOT = ROOT / "configs" / "composites"
CLASSIFICATIONS = {"structural", "join_safety", "derived_child", "business_only"}
BUCKETS = (
    "required_fields",
    "columns",
    "ranges",
    "exclude_if_present",
    "list_length",
    "list_contains",
)
SHADOW_CHECK_TYPES = {"join_cardinality", "field_sparsity", "gold_projection_delta"}
EXPECTED_SHADOW_METRICS = {
    "current_rejections": "bioetl_silver_filter_rejections_total",
    "structural_shadow_comparisons": "bioetl_structural_policy_shadow_comparisons_total",
}


def _load_inventory() -> dict[str, Any]:
    payload = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict), (
        "silver_filter_boundary_inventory.yaml must be a mapping"
    )
    return payload


def _composite_pipeline_ids() -> set[str]:
    return {
        f"composite_{path.stem}"
        for path in COMPOSITE_CONFIG_ROOT.glob("*.yaml")
        if path.is_file()
    }


def _pipeline_id(config: dict[str, Any]) -> str:
    return f"{config['provider']}_{config['entity']}"


def _iter_active_silver_filters() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for path in sorted(ENTITY_CONFIG_ROOT.rglob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        filters = payload.get("filters") or {}
        silver_filters = filters.get("silver_filters") or {}
        if any(silver_filters.get(bucket) for bucket in BUCKETS):
            rows.append((str(path.relative_to(ROOT)), payload, silver_filters))
    return rows


def _actual_rule_names(bucket: str, bucket_payload: Any) -> set[str]:
    if bucket in {"required_fields", "exclude_if_present"}:
        return {str(item) for item in (bucket_payload or [])}
    if bucket in {"columns", "ranges", "list_length", "list_contains"}:
        return {str(key) for key in (bucket_payload or {})}
    raise AssertionError(f"Unexpected bucket: {bucket}")


def _inventory_rule_names(rule_payload: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for classification, values in rule_payload.items():
        assert classification in CLASSIFICATIONS, (
            f"Unsupported Silver filter classification {classification!r}; "
            f"allowed: {sorted(CLASSIFICATIONS)}"
        )
        assert isinstance(values, list), (
            "Silver filter inventory classification values must be lists, "
            f"got {type(values).__name__}"
        )
        names.update(str(value) for value in values)
    return names


def test_inventory_has_expected_shape() -> None:
    payload = _load_inventory()
    assert payload.get("version") == 1
    assert "pipelines" in payload
    assert isinstance(payload["pipelines"], dict)
    assert "safe_first_wave_candidates" in payload
    assert isinstance(payload["safe_first_wave_candidates"], list)

    if not payload["safe_first_wave_candidates"]:
        assert payload.get("safe_first_wave_rationale"), (
            "Empty safe_first_wave_candidates requires explicit rationale"
        )


def test_every_active_silver_filter_pipeline_has_inventory_row() -> None:
    payload = _load_inventory()
    inventory_rows = payload["pipelines"]

    missing: list[str] = []
    for relative_path, config, _silver_filters in _iter_active_silver_filters():
        pipeline_id = _pipeline_id(config)
        if pipeline_id not in inventory_rows:
            missing.append(f"{pipeline_id} ({relative_path})")

    assert not missing, "Missing Silver filter boundary inventory rows:\n" + "\n".join(
        missing
    )


def test_inventory_covers_every_active_silver_rule_exactly_by_name() -> None:
    payload = _load_inventory()
    inventory_rows = payload["pipelines"]

    violations: list[str] = []
    for relative_path, config, silver_filters in _iter_active_silver_filters():
        pipeline_id = _pipeline_id(config)
        row = inventory_rows[pipeline_id]
        filters = row.get("filters")
        if not isinstance(filters, dict):
            violations.append(f"{pipeline_id}: filters mapping missing")
            continue

        for bucket in BUCKETS:
            actual_payload = silver_filters.get(bucket)
            actual_names = _actual_rule_names(bucket, actual_payload)
            if not actual_names:
                continue

            inventory_payload = filters.get(bucket)
            if not isinstance(inventory_payload, dict):
                violations.append(
                    f"{pipeline_id}: inventory bucket {bucket} missing for {relative_path}"
                )
                continue

            inventory_names = _inventory_rule_names(inventory_payload)
            if actual_names != inventory_names:
                violations.append(
                    f"{pipeline_id}: inventory bucket {bucket} mismatch\n"
                    f"  actual={sorted(actual_names)}\n"
                    f"  inventory={sorted(inventory_names)}"
                )

    assert not violations, "\n".join(violations)


def test_business_only_rules_require_migration_metadata() -> None:
    payload = _load_inventory()

    violations: list[str] = []
    for pipeline_id, row in payload["pipelines"].items():
        filters = row.get("filters") or {}
        has_business_only = any(
            isinstance(bucket_payload, dict) and bucket_payload.get("business_only")
            for bucket_payload in filters.values()
        )
        migration = row.get("business_only_migration")
        if not has_business_only:
            continue
        if not isinstance(migration, dict):
            violations.append(
                f"{pipeline_id}: business_only rules require business_only_migration metadata"
            )
            continue
        state = migration.get("state")
        assert state in {
            "blocked_by_downstream_composite",
            "candidate_for_gold",
            "migrated_to_gold",
        }, f"{pipeline_id}: unsupported business_only_migration.state={state!r}"
        if state == "blocked_by_downstream_composite":
            blocked_by = migration.get("blocked_by")
            if not isinstance(blocked_by, list) or not blocked_by:
                violations.append(
                    f"{pipeline_id}: blocked_by_downstream_composite requires blocked_by list"
                )

    assert not violations, "\n".join(violations)


def test_blocked_business_only_rules_require_shadow_analysis_metadata() -> None:
    payload = _load_inventory()
    composite_ids = _composite_pipeline_ids()
    violations: list[str] = []

    for pipeline_id, row in payload["pipelines"].items():
        migration = row.get("business_only_migration") or {}
        if migration.get("state") != "blocked_by_downstream_composite":
            continue

        shadow_analysis = row.get("shadow_analysis")
        if not isinstance(shadow_analysis, dict):
            violations.append(
                f"{pipeline_id}: blocked business_only migration requires shadow_analysis block"
            )
            continue

        shadow_metrics = shadow_analysis.get("shadow_metrics")
        if not isinstance(shadow_metrics, dict):
            violations.append(
                f"{pipeline_id}: shadow_analysis.shadow_metrics must be a mapping"
            )
        else:
            for metric_key, expected_metric_name in EXPECTED_SHADOW_METRICS.items():
                entry = shadow_metrics.get(metric_key)
                if not isinstance(entry, dict):
                    violations.append(
                        f"{pipeline_id}: shadow metric {metric_key} must be a mapping"
                    )
                    continue
                metric_name = entry.get("metric")
                if metric_name != expected_metric_name:
                    violations.append(
                        f"{pipeline_id}: shadow metric {metric_key} must reference "
                        f"{expected_metric_name!r}, got {metric_name!r}"
                    )
                if metric_name not in REGISTERED_PROMETHEUS_METRIC_NAMES:
                    violations.append(
                        f"{pipeline_id}: shadow metric {metric_name!r} is not registered"
                    )
                labels = entry.get("labels")
                if not isinstance(labels, list) or not labels:
                    violations.append(
                        f"{pipeline_id}: shadow metric {metric_key} requires labels list"
                    )

        checks = shadow_analysis.get("composite_impact_checks")
        if not isinstance(checks, list) or not checks:
            violations.append(
                f"{pipeline_id}: shadow_analysis.composite_impact_checks must be non-empty"
            )
            continue

        blocked_by = migration.get("blocked_by") or []
        referenced_composites = {
            check.get("composite_pipeline")
            for check in checks
            if isinstance(check, dict)
        }
        if not set(blocked_by) <= referenced_composites:
            violations.append(
                f"{pipeline_id}: composite_impact_checks must cover blocked_by composites"
            )

        for check in checks:
            if not isinstance(check, dict):
                violations.append(
                    f"{pipeline_id}: composite impact checks must contain mappings"
                )
                continue
            composite_pipeline = check.get("composite_pipeline")
            if composite_pipeline not in composite_ids:
                violations.append(
                    f"{pipeline_id}: unknown composite_pipeline {composite_pipeline!r}"
                )
            check_type = check.get("check_type")
            if check_type not in SHADOW_CHECK_TYPES:
                violations.append(
                    f"{pipeline_id}: unsupported composite check_type {check_type!r}"
                )
            payload_key = "keys" if check_type == "join_cardinality" else "fields"
            payload_values = check.get(payload_key)
            if not isinstance(payload_values, list) or not payload_values:
                violations.append(
                    f"{pipeline_id}: {check_type} requires non-empty {payload_key} list"
                )

    assert not violations, "\n".join(violations)


def test_shadow_candidate_rules_match_business_only_inventory() -> None:
    payload = _load_inventory()
    violations: list[str] = []

    for pipeline_id, row in payload["pipelines"].items():
        migration = row.get("business_only_migration") or {}
        if migration.get("state") != "blocked_by_downstream_composite":
            continue

        shadow_analysis = row.get("shadow_analysis") or {}
        candidate_rules = shadow_analysis.get("candidate_business_rules")
        if not isinstance(candidate_rules, dict):
            violations.append(
                f"{pipeline_id}: candidate_business_rules mapping missing"
            )
            continue

        filters = row.get("filters") or {}
        for bucket in BUCKETS:
            filter_bucket = filters.get(bucket)
            if not isinstance(filter_bucket, dict):
                continue
            expected = set(filter_bucket.get("business_only") or [])
            actual = set(candidate_rules.get(bucket) or [])
            if expected != actual:
                violations.append(
                    f"{pipeline_id}: candidate_business_rules {bucket} mismatch\n"
                    f"  expected={sorted(expected)}\n"
                    f"  actual={sorted(actual)}"
                )

    assert not violations, "\n".join(violations)


def test_inventory_baseline_outputs_match_generator(tmp_path: Path) -> None:
    """Keep committed ADR-048 inventory artifacts tied to the scanner output."""
    plans = [
        build_entity_plan(provider, entity, path)
        for provider, entity, path in discover_entity_configs()
    ]

    generated_csv = tmp_path / CSV_OUT.name
    generated_json = tmp_path / JSON_OUT.name
    generated_md = tmp_path / MD_OUT.name
    write_csv(plans, generated_csv)
    write_json(plans, generated_json)
    write_markdown(plans, generated_md)

    mismatches: list[str] = []
    for expected_path, actual_path in (
        (CSV_OUT, generated_csv),
        (JSON_OUT, generated_json),
        (MD_OUT, generated_md),
    ):
        if expected_path.read_text(encoding="utf-8") != actual_path.read_text(
            encoding="utf-8"
        ):
            mismatches.append(str(expected_path.relative_to(ROOT)))

    assert not mismatches, (
        "ADR-048 inventory baseline drifted from generator output. "
        "Run: python scripts/data_quality/inventory_silver_filters_migration.py\n"
        + "\n".join(mismatches)
    )

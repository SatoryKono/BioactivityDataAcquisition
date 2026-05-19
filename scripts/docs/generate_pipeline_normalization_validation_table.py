#!/usr/bin/env python3
"""Generate per-pipeline normalization and validation summary artifacts."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_CSV = (
    ROOT
    / "docs/reports/generated/pipeline_normalization_field_matrix"
    / "pipeline_normalization_field_matrix.csv"
)
OUT_DIR = ROOT / "docs/reports/generated/pipeline_normalization_validation_table"
OUT_CSV = OUT_DIR / "pipeline_normalization_validation_table.csv"
OUT_MD = OUT_DIR / "pipeline_normalization_validation_table.md"

SYSTEM_FIELDS = {
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_index",
    "_state",
    "_dq_error",
    "_dq_warn",
}

CSV_COLUMNS = (
    "provider",
    "pipeline_name",
    "pipeline_kind",
    "field_count",
    "business_field_count",
    "normalization_summary",
    "top_normalizers",
    "identifier_ontology_summary",
    "structured_payload_summary",
    "schema_validation_summary",
    "dq_matrix_summary",
    "field_validation_summary",
    "cross_field_validation_count",
    "conditional_validation_count",
    "key_nullability_count",
    "threshold_summary",
    "composite_join_summary",
    "source_refs",
)

SEMANTIC_LABELS = {
    "free_text": "free-text cleanup",
    "reference_identifier": "reference IDs",
    "canonical_identifier": "canonical IDs",
    "ontology_reference_identifier": "ontology IDs",
    "ontology_reference_metadata": "ontology companion metadata",
    "controlled_vocabulary": "controlled vocabularies",
    "strict_enum": "strict enums",
    "strict_flag": "strict flags",
    "strict_boolean": "strict booleans",
    "structured_json": "structured JSON",
    "canonical_json": "canonical JSON",
    "derived_vocabulary": "derived vocabularies",
    "join_key_policy": "join-key policies",
    "upstream_inherited": "upstream inherited fields",
    "technical_passthrough": "technical passthrough",
}


def _read_matrix_rows() -> list[dict[str, str]]:
    with MATRIX_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _collect_entity_configs() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "configs/entities").rglob("*.yaml")):
        data = _load_yaml(path)
        pipeline = data.get("pipeline", {}).get("pipeline_name")
        if not pipeline:
            continue
        registry[pipeline] = {"config_path": path, "config": data}
    return registry


def _collect_composite_configs() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "configs/composites").glob("*.yaml")):
        data = _load_yaml(path)
        composite = data.get("composite", {})
        pipeline = composite.get("name")
        if not pipeline:
            continue
        dq_rel = composite.get("dq_overrides", {}).get("dq_config_file")
        dq_path = (path.parent / dq_rel).resolve() if dq_rel else None
        dq_config = _load_yaml(dq_path) if dq_path and dq_path.exists() else {}
        registry[pipeline] = {
            "config_path": path,
            "config": data,
            "dq_config_path": dq_path,
            "dq_config": dq_config,
        }
    return registry


def _top_terms(counter: Counter[str], *, limit: int = 4) -> str:
    items = [(name, count) for name, count in counter.items() if name]
    if not items:
        return "n/a"
    ranked = sorted(items, key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{name}×{count}" for name, count in ranked)


def _top_semantics(counter: Counter[str], *, limit: int = 5) -> str:
    items = [
        (SEMANTIC_LABELS.get(name, name), count)
        for name, count in counter.items()
        if name and name != "not_applicable"
    ]
    if not items:
        return "n/a"
    ranked = sorted(items, key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{name}×{count}" for name, count in ranked)


def _schema_summary(rows: list[dict[str, str]]) -> str:
    schema_values = [row["schema_coverage"] for row in rows]
    inherited = sum(value == "gold_contract:inherited" for value in schema_values)
    if inherited == len(schema_values):
        return f"gold_contract:inherited on all {len(schema_values)} fields"
    silver_present = sum("silver_arrow:present" in value for value in schema_values)
    domain_missing = sum("domain_schema:missing" in value for value in schema_values)
    domain_present = len(schema_values) - domain_missing
    constrained = sum("checks=" in value and not value.endswith("checks=none)") for value in schema_values)
    return (
        f"silver {silver_present}/{len(schema_values)}; "
        f"domain {domain_present}/{len(schema_values)}; "
        f"domain_missing {domain_missing}; "
        f"constrained_checks {constrained}"
    )


def _dq_matrix_summary(rows: list[dict[str, str]]) -> str:
    dq = Counter(row["dq_coverage"] for row in rows if row["dq_coverage"])
    configured = sum(
        count
        for name, count in dq.items()
        if name not in {"not_configured", "not_applicable"}
    )
    warn = sum(count for name, count in dq.items() if "warn" in name)
    parts = [f"configured_fields {configured}/{len(rows)}"]
    if "not_configured" in dq:
        parts.append(f"not_configured {dq['not_configured']}")
    if "not_applicable" in dq:
        parts.append(f"not_applicable {dq['not_applicable']}")
    if warn:
        parts.append(f"warning_rules {warn}")
    top_rules = _top_terms(
        Counter(
            {
                name: count
                for name, count in dq.items()
                if name not in {"not_configured", "not_applicable"}
            }
        ),
        limit=3,
    )
    if top_rules != "n/a":
        parts.append(f"top {top_rules}")
    return "; ".join(parts)


def _validation_summary(validations: list[dict[str, Any]]) -> str:
    if not validations:
        return "none"
    counter = Counter(str(item.get("type", "unknown")) for item in validations)
    return ", ".join(f"{name}×{count}" for name, count in sorted(counter.items()))


def _threshold_summary(config: dict[str, Any], dq_config: dict[str, Any] | None = None) -> str:
    quality = config.get("quality", {})
    dq_overrides = quality if "soft_fail_threshold" in quality else {}
    if dq_config:
        dq_overrides = dq_config.get("dq_overrides", {}) or {}
    parts: list[str] = []
    for key in ("soft_fail_threshold", "hard_fail_threshold", "warning_threshold", "quarantine_threshold"):
        value = dq_overrides.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    required = dq_overrides.get("required_fields")
    if required:
        parts.append(f"required_fields={','.join(required)}")
    return "; ".join(parts) if parts else "default"


def _composite_join_summary(config: dict[str, Any]) -> str:
    composite = config.get("composite", {})
    dependencies = composite.get("dependencies", []) or []
    if not dependencies:
        return "n/a"
    pieces: list[str] = []
    for dependency in dependencies:
        pipeline = dependency.get("pipeline", "unknown")
        join_keys = ",".join(dependency.get("join_keys", []) or [])
        filter_fields = ",".join(dependency.get("filter_fields", []) or [])
        pieces.append(f"{pipeline}[join={join_keys};filter={filter_fields}]")
    return "; ".join(pieces)


def _source_refs(*paths: Path | None) -> str:
    refs = [str(path.relative_to(ROOT)) for path in paths if path is not None]
    return "; ".join(refs)


def _business_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["field_name"] not in SYSTEM_FIELDS]


def build_rows() -> list[dict[str, str]]:
    matrix_rows = _read_matrix_rows()
    entity_configs = _collect_entity_configs()
    composite_configs = _collect_composite_configs()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in matrix_rows:
        grouped[row["pipeline_name"]].append(row)

    output: list[dict[str, str]] = []
    for pipeline_name in sorted(grouped):
        rows = grouped[pipeline_name]
        sample = rows[0]
        business_rows = _business_rows(rows)
        normalizers = Counter(row["normalizer"] for row in business_rows if row["normalizer"])
        semantic_categories = Counter(row["semantic_category"] for row in business_rows if row["semantic_category"])
        identifier_ontology = Counter(
            row["semantic_category"]
            for row in business_rows
            if row["semantic_category"]
            in {
                "reference_identifier",
                "canonical_identifier",
                "ontology_reference_identifier",
                "ontology_reference_metadata",
            }
        )
        structured_payloads = Counter(
            row["normalizer"]
            for row in business_rows
            if "json" in row["normalizer"] or row["semantic_category"] in {"structured_json", "canonical_json"}
        )

        if sample["pipeline_kind"] == "entity":
            config_entry = entity_configs[pipeline_name]
            config = config_entry["config"]
            quality = config.get("quality", {})
            source_refs = _source_refs(config_entry["config_path"], MATRIX_CSV)
            threshold_summary = _threshold_summary(config)
            composite_join_summary = "n/a"
        else:
            config_entry = composite_configs[pipeline_name]
            config = config_entry["config"]
            quality = {}
            source_refs = _source_refs(
                config_entry["config_path"], config_entry.get("dq_config_path"), MATRIX_CSV
            )
            threshold_summary = _threshold_summary(config, config_entry.get("dq_config"))
            composite_join_summary = _composite_join_summary(config)

        output.append(
            {
                "provider": sample["provider"],
                "pipeline_name": pipeline_name,
                "pipeline_kind": sample["pipeline_kind"],
                "field_count": str(len(rows)),
                "business_field_count": str(len(business_rows)),
                "normalization_summary": _top_semantics(semantic_categories),
                "top_normalizers": _top_terms(normalizers, limit=6),
                "identifier_ontology_summary": _top_semantics(identifier_ontology, limit=4),
                "structured_payload_summary": _top_terms(structured_payloads, limit=4),
                "schema_validation_summary": _schema_summary(rows),
                "dq_matrix_summary": _dq_matrix_summary(rows),
                "field_validation_summary": _validation_summary(
                    quality.get("entity_field_validations", []) or []
                ),
                "cross_field_validation_count": str(
                    len(quality.get("entity_cross_field_validations", []) or [])
                ),
                "conditional_validation_count": str(
                    len(quality.get("entity_conditional_validations", []) or [])
                ),
                "key_nullability_count": str(len(quality.get("key_nullability", []) or [])),
                "threshold_summary": threshold_summary,
                "composite_join_summary": composite_join_summary,
                "source_refs": source_refs,
            }
        )
    return output


def _markdown_table(rows: list[dict[str, str]]) -> str:
    headers = list(CSV_COLUMNS)
    lines = [
        "# Pipeline Normalization And Validation Table",
        "",
        "Generated from `pipeline_normalization_field_matrix.csv`, entity/composite pipeline configs,",
        "and composite DQ override files. One row equals one pipeline.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [row[column].replace("\n", " ").strip() for column in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _write_csv(rows: list[dict[str, str]]) -> None:
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = build_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(rows)
    OUT_MD.write_text(_markdown_table(rows), encoding="utf-8")
    print(f"Wrote {OUT_CSV.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

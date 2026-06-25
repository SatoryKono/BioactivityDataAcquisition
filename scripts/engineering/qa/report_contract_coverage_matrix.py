#!/usr/bin/env python3
"""Generate deterministic contract coverage matrix artifacts for active entity configs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIGS_ROOT = PROJECT_ROOT / "configs"
ENTITIES_ROOT = CONFIGS_ROOT / "entities"
REGISTRY_PATH = CONFIGS_ROOT / "base" / "contract_registry.yaml"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.md"
GENERIC_GOLD_CONTRACT_TEST_PATHS = (
    "tests/contract/test_gold_entity_coverage_complete.py",
    "tests/contract/test_gold_pk_consistency.py",
    "tests/contract/test_gold_schema_strict_violations.py",
)
GENERIC_GOLDEN_CONTRACT_TEST_PATHS = (
    "tests/contract/test_gold_dq_golden_snapshots.py",
    "tests/fixtures/golden/gold/schema_registry.v1.json",
)
PANDERA_CONSTRAINT_KEYS = frozenset(
    {
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "maximum",
        "maxLength",
        "minimum",
        "minLength",
        "pattern",
    }
)
PANDERA_CONTRACT_BASE_MARKERS = (
    "pa.DataFrameModel",
    "StrictGoldContractSchema",
    "CompositeGoldCommonSchema",
    "CompositeLookupLineageSchema",
    "PublicationGoldCommonSchema",
)
STRICT_GOLD_VALIDATION_MARKERS = (
    "StrictGoldContractSchema",
    "CompositeGoldCommonSchema",
    "CompositeLookupLineageSchema",
    "PublicationGoldCommonSchema",
    "strict = True",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected mapping in {path.as_posix()}"
        raise TypeError(msg)
    return payload


def _gold_runtime_enabled(pipeline: dict[str, Any]) -> bool:
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return True
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


def _registry_entries() -> dict[str, dict[str, Any]]:
    payload = _load_yaml(REGISTRY_PATH)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        msg = f"Expected entries mapping in {REGISTRY_PATH.as_posix()}"
        raise TypeError(msg)
    normalized: dict[str, dict[str, Any]] = {}
    for contract_ref, entry in entries.items():
        if not isinstance(contract_ref, str) or not isinstance(entry, dict):
            continue
        normalized[contract_ref] = entry
    return normalized


def _resolve_registry_relative(path: str) -> Path:
    return (REGISTRY_PATH.parent / path).resolve()


def _relativize(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _relative_if_project_path(path: Path) -> str:
    try:
        return _relativize(path)
    except ValueError:
        return path.as_posix()


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _contract_artifact_summary(paths: list[str]) -> dict[str, Any]:
    artifacts = [
        _load_json_if_exists(_resolve_registry_relative(path)) for path in paths
    ]
    artifacts = [artifact for artifact in artifacts if artifact]
    if not artifacts:
        return {
            "published_contract_schema_version": "",
            "published_contract_property_count": 0,
            "published_contract_required_count": 0,
            "published_contract_nullable_count": 0,
            "published_contract_non_nullable_count": 0,
            "published_contract_check_constraint_count": 0,
            "published_contract_nullable_policy_declared": False,
            "published_contract_required_fields": [],
        }

    properties: dict[str, Any] = {}
    required_fields: set[str] = set()
    schema_versions: set[str] = set()
    for artifact in artifacts:
        schema_version = artifact.get("$version")
        if isinstance(schema_version, str) and schema_version:
            schema_versions.add(schema_version)
        artifact_properties = artifact.get("properties")
        if isinstance(artifact_properties, dict):
            properties.update(artifact_properties)
        required_fields.update(_string_list(artifact.get("required")))

    nullable_count = 0
    non_nullable_count = 0
    check_constraint_count = 0
    for property_payload in properties.values():
        if not isinstance(property_payload, dict):
            continue
        if property_payload.get("nullable") is True:
            nullable_count += 1
        else:
            non_nullable_count += 1
        if PANDERA_CONSTRAINT_KEYS.intersection(property_payload):
            check_constraint_count += 1

    return {
        "published_contract_schema_version": ",".join(sorted(schema_versions)),
        "published_contract_property_count": len(properties),
        "published_contract_required_count": len(required_fields),
        "published_contract_nullable_count": nullable_count,
        "published_contract_non_nullable_count": non_nullable_count,
        "published_contract_check_constraint_count": check_constraint_count,
        "published_contract_nullable_policy_declared": (
            bool(properties) and nullable_count + non_nullable_count == len(properties)
        ),
        "published_contract_required_fields": sorted(required_fields),
    }


def _schema_source_summary(source_path: str) -> dict[str, Any]:
    source_file = _resolve_registry_relative(source_path) if source_path else None
    source_text = (
        source_file.read_text(encoding="utf-8")
        if source_file is not None and source_file.is_file()
        else ""
    )
    pandera_contract_declared = any(
        marker in source_text for marker in PANDERA_CONTRACT_BASE_MARKERS
    )
    gold_strict_validation_declared = any(
        marker in source_text for marker in STRICT_GOLD_VALIDATION_MARKERS
    )
    return {
        "pandera_contract_declared": pandera_contract_declared,
        "gold_strict_validation_declared": gold_strict_validation_declared,
        "pandera_field_count_in_source": source_text.count("pa.Field("),
        "pandera_check_count_in_source": sum(
            source_text.count(token)
            for token in (
                "str_matches=",
                "isin=",
                "ge=",
                "gt=",
                "le=",
                "lt=",
                "@pa.check",
            )
        ),
    }


def _primary_key_fields(pipeline: dict[str, Any]) -> list[str]:
    business_primary_keys = _string_list(pipeline.get("business_primary_keys"))
    technical_primary_key = pipeline.get("technical_primary_key")
    fields = list(business_primary_keys)
    if isinstance(technical_primary_key, str) and technical_primary_key:
        fields.insert(0, technical_primary_key)
    return sorted(set(fields))


def _contract_test_index() -> list[tuple[str, str]]:
    indexed_paths: list[tuple[str, str]] = []
    for test_path in sorted((PROJECT_ROOT / "tests").rglob("test*.py")):
        relative_path = _relativize(test_path)
        indexed_paths.append((relative_path, relative_path.lower()))
    return indexed_paths


def _contract_test_paths(
    provider: str,
    entity: str,
    test_index: list[tuple[str, str]],
) -> list[str]:
    needles = {
        f"{provider}_{entity}",
        f"{provider}.{entity}",
        entity,
    }
    paths: set[str] = {
        path
        for path in GENERIC_GOLD_CONTRACT_TEST_PATHS
        if (PROJECT_ROOT / path).is_file()
    }
    for relative_path, lowered_path in test_index:
        if relative_path in paths:
            continue
        if any(needle.lower() in lowered_path for needle in needles):
            paths.add(relative_path)
    return sorted(paths)


def _golden_contract_test_paths(contract_test_paths: list[str]) -> list[str]:
    paths = {
        path
        for path in contract_test_paths
        if "golden" in path.lower()
    }
    paths.update(
        path
        for path in GENERIC_GOLDEN_CONTRACT_TEST_PATHS
        if (PROJECT_ROOT / path).is_file()
    )
    return sorted(paths)


def _constraint_completeness(
    *,
    gold_enabled: bool,
    schema_source_summary: dict[str, Any],
    contract_artifact_summary: dict[str, Any],
    primary_keys_required: bool,
    contract_test_paths: list[str],
    golden_test_paths: list[str],
) -> tuple[str, list[str], list[str]]:
    if not gold_enabled:
        return "excluded", [], []

    missing: list[str] = []
    if schema_source_summary["pandera_field_count_in_source"] <= 0:
        missing.append("pandera_fields")
    if contract_artifact_summary["published_contract_property_count"] <= 0:
        missing.append("published_contract_properties")
    if not contract_artifact_summary["published_contract_nullable_policy_declared"]:
        missing.append("nullable_policy")
    if contract_artifact_summary["published_contract_required_count"] <= 0:
        missing.append("required_fields")
    if not primary_keys_required:
        missing.append("primary_key_required_fields")
    if not contract_test_paths:
        missing.append("contract_tests")
    if not golden_test_paths:
        missing.append("golden_tests")

    surfaces: list[str] = []
    if schema_source_summary["pandera_field_count_in_source"] > 0:
        surfaces.append("pandera_fields")
    if schema_source_summary["pandera_check_count_in_source"] > 0:
        surfaces.append("pandera_checks")
    if contract_artifact_summary["published_contract_nullable_policy_declared"]:
        surfaces.append("nullable_policy")
    if contract_artifact_summary["published_contract_required_count"] > 0:
        surfaces.append("required_fields")
    if primary_keys_required:
        surfaces.append("primary_key_required_fields")
    if contract_test_paths:
        surfaces.append("contract_tests")
    if golden_test_paths:
        surfaces.append("golden_tests")

    status = "covered" if not missing else "missing_constraint_evidence"
    return status, sorted(surfaces), sorted(missing)


def _build_row(
    *,
    config_path: Path,
    config_payload: dict[str, Any],
    registry_entries: dict[str, dict[str, Any]],
    test_index: list[tuple[str, str]],
) -> dict[str, Any]:
    provider = str(config_payload.get("provider") or config_path.parent.name)
    entity = str(config_payload.get("entity") or config_path.stem)
    pipeline = config_payload.get("pipeline")
    if not isinstance(pipeline, dict):
        pipeline = {}
    pipeline_name = str(pipeline.get("pipeline_name") or f"{provider}_{entity}")
    contract_ref = f"{provider}.{entity}"
    gold_enabled = _gold_runtime_enabled(pipeline)
    primary_key_fields = _primary_key_fields(pipeline)

    contract_yaml_path = CONFIGS_ROOT / "contracts" / provider / f"{entity}.yaml"
    contract_yaml_exists = contract_yaml_path.is_file()
    contract_payload = _load_yaml(contract_yaml_path) if contract_yaml_exists else {}

    registry_entry = registry_entries.get(contract_ref)
    registry_entry_exists = registry_entry is not None
    registry_identity = (
        registry_entry.get("identity", {}) if isinstance(registry_entry, dict) else {}
    )
    if not isinstance(registry_identity, dict):
        registry_identity = {}

    source_path = (
        str(registry_entry.get("source_path", ""))
        if isinstance(registry_entry, dict)
        else ""
    )
    source_exists = (
        bool(source_path) and _resolve_registry_relative(source_path).is_file()
    )

    published_artifacts = (
        _string_list(registry_entry.get("published_artifacts"))
        if isinstance(registry_entry, dict)
        else []
    )
    published_artifact_missing_paths = [
        artifact
        for artifact in published_artifacts
        if not _resolve_registry_relative(artifact).is_file()
    ]
    contract_artifact_summary = _contract_artifact_summary(published_artifacts)
    schema_source_summary = _schema_source_summary(source_path)
    contract_test_paths = _contract_test_paths(provider, entity, test_index)
    golden_test_paths = _golden_contract_test_paths(contract_test_paths)
    required_fields = contract_artifact_summary["published_contract_required_fields"]
    primary_keys_required = all(
        field in required_fields for field in primary_key_fields
    )
    (
        constraint_completeness_status,
        constraint_completeness_surfaces,
        missing_constraint_surfaces,
    ) = _constraint_completeness(
        gold_enabled=gold_enabled,
        schema_source_summary=schema_source_summary,
        contract_artifact_summary=contract_artifact_summary,
        primary_keys_required=primary_keys_required,
        contract_test_paths=contract_test_paths,
        golden_test_paths=golden_test_paths,
    )

    missing_surfaces: list[str] = []
    if not contract_yaml_exists:
        missing_surfaces.append("contract_yaml")
    if not registry_entry_exists:
        missing_surfaces.append("registry_entry")
    if not source_path:
        missing_surfaces.append("gold_schema_source_path")
    elif not source_exists:
        missing_surfaces.append("gold_schema_source_file")
    if not published_artifacts:
        missing_surfaces.append("published_artifact")
    elif published_artifact_missing_paths:
        missing_surfaces.append("published_artifact_file")
    if gold_enabled:
        if not schema_source_summary["pandera_contract_declared"]:
            missing_surfaces.append("pandera_contract_source")
        if not schema_source_summary["gold_strict_validation_declared"]:
            missing_surfaces.append("gold_strict_validation")
        if not primary_key_fields:
            missing_surfaces.append("primary_key_contract")
        elif not primary_keys_required:
            missing_surfaces.append("primary_key_required_fields")
        if contract_artifact_summary["published_contract_property_count"] <= 0:
            missing_surfaces.append("published_contract_properties")
        if contract_artifact_summary["published_contract_required_count"] <= 0:
            missing_surfaces.append("published_contract_required_fields")
        if not contract_test_paths:
            missing_surfaces.append("contract_tests")

    yaml_contract_ref = contract_payload.get("contract_ref")
    yaml_contract_version = contract_payload.get("contract_version")
    registry_contract_version = registry_identity.get("contract_version")
    if contract_yaml_exists and yaml_contract_ref != contract_ref:
        missing_surfaces.append("contract_ref_mismatch")
    if contract_yaml_exists and registry_entry_exists:
        if yaml_contract_version != registry_contract_version:
            missing_surfaces.append("contract_version_mismatch")

    parity_status = "covered"
    exclusion_reason = ""
    if not gold_enabled:
        parity_status = "excluded"
        exclusion_reason = "gold_runtime_disabled"
    elif missing_surfaces:
        parity_status = "missing_surfaces"

    return {
        "pipeline_name": pipeline_name,
        "provider": provider,
        "entity": entity,
        "contract_ref": contract_ref,
        "dataset_layer": "gold",
        "config_path": _relativize(config_path),
        "gold_enabled": gold_enabled,
        "parity_status": parity_status,
        "exclusion_reason": exclusion_reason,
        "contract_yaml_path": (
            _relativize(contract_yaml_path) if contract_yaml_exists else ""
        ),
        "contract_yaml_exists": contract_yaml_exists,
        "contract_yaml_contract_ref": (
            str(yaml_contract_ref) if isinstance(yaml_contract_ref, str) else ""
        ),
        "contract_yaml_contract_version": (
            str(yaml_contract_version) if isinstance(yaml_contract_version, str) else ""
        ),
        "registry_entry_exists": registry_entry_exists,
        "registry_status": (
            str(registry_entry.get("status", ""))
            if isinstance(registry_entry, dict)
            else ""
        ),
        "registry_contract_version": (
            str(registry_contract_version)
            if isinstance(registry_contract_version, str)
            else ""
        ),
        "gold_schema_source_path": source_path,
        "gold_schema_source_exists": source_exists,
        "gold_schema_source_resolved_path": (
            _relative_if_project_path(_resolve_registry_relative(source_path))
            if source_path
            else ""
        ),
        "pandera_contract_declared": schema_source_summary["pandera_contract_declared"],
        "gold_strict_validation_declared": schema_source_summary[
            "gold_strict_validation_declared"
        ],
        "pandera_field_count_in_source": schema_source_summary[
            "pandera_field_count_in_source"
        ],
        "pandera_check_count_in_source": schema_source_summary[
            "pandera_check_count_in_source"
        ],
        "primary_key_fields": primary_key_fields,
        "primary_key_required_in_published_contract": primary_keys_required,
        "uniqueness_constraint_source": (
            "pipeline.business_primary_keys" if primary_key_fields else ""
        ),
        "contract_test_paths": contract_test_paths,
        "golden_test_paths": golden_test_paths,
        "golden_test_evidence_declared": bool(golden_test_paths),
        "constraint_completeness_status": constraint_completeness_status,
        "constraint_completeness_surfaces": constraint_completeness_surfaces,
        "missing_constraint_surfaces": missing_constraint_surfaces,
        "pandera_check_constraint_evidence_declared": (
            schema_source_summary["pandera_check_count_in_source"] > 0
            or contract_artifact_summary["published_contract_check_constraint_count"] > 0
        ),
        "published_artifact_paths": published_artifacts,
        "published_artifact_missing_paths": published_artifact_missing_paths,
        **contract_artifact_summary,
        "missing_surfaces": sorted(set(missing_surfaces)),
    }


def _collect_rows() -> list[dict[str, Any]]:
    registry_entries = _registry_entries()
    test_index = _contract_test_index()
    rows: list[dict[str, Any]] = []
    for config_path in sorted(ENTITIES_ROOT.glob("*/*.yaml")):
        rows.append(
            _build_row(
                config_path=config_path,
                config_payload=_load_yaml(config_path),
                registry_entries=registry_entries,
                test_index=test_index,
            )
        )
    return rows


def _existing_snapshot_date(path: Path) -> str | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    snapshot_date = payload.get("snapshot_date")
    return snapshot_date if isinstance(snapshot_date, str) else None


def build_payload(*, snapshot_date: str | None = None) -> dict[str, Any]:
    rows = _collect_rows()
    covered_gold_enabled_count = sum(
        1 for row in rows if row["gold_enabled"] and row["parity_status"] == "covered"
    )
    gold_enabled_count = sum(1 for row in rows if row["gold_enabled"])
    excluded_rows = [row for row in rows if row["parity_status"] == "excluded"]
    constraint_missing_rows = [
        row
        for row in rows
        if row["gold_enabled"]
        and row["constraint_completeness_status"] != "covered"
    ]
    return {
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "row_count": len(rows),
        "gold_enabled_count": gold_enabled_count,
        "covered_gold_enabled_count": covered_gold_enabled_count,
        "missing_gold_enabled_count": gold_enabled_count - covered_gold_enabled_count,
        "constraint_completeness_review_count": gold_enabled_count,
        "constraint_completeness_missing_count": len(constraint_missing_rows),
        "golden_test_evidence_count": sum(
            1 for row in rows if row["golden_test_evidence_declared"]
        ),
        "excluded_count": len(excluded_rows),
        "exclusions": [
            {
                "pipeline_name": row["pipeline_name"],
                "contract_ref": row["contract_ref"],
                "reason": row["exclusion_reason"],
            }
            for row in excluded_rows
        ],
        "rows": rows,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Contract Coverage Matrix",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- row_count: {payload['row_count']}",
        f"- gold_enabled_count: {payload['gold_enabled_count']}",
        f"- covered_gold_enabled_count: {payload['covered_gold_enabled_count']}",
        f"- missing_gold_enabled_count: {payload['missing_gold_enabled_count']}",
        "- constraint_completeness_missing_count: "
        f"{payload['constraint_completeness_missing_count']}",
        f"- golden_test_evidence_count: {payload['golden_test_evidence_count']}",
        f"- excluded_count: {payload['excluded_count']}",
        "",
        "| pipeline_name | layer | contract_ref | gold_enabled | parity_status | "
        "constraint_status | strict | properties | required | checks | pk_fields | "
        "tests | golden | missing_surfaces | missing_constraints |",
        "| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        render_row = dict(row)
        render_row["missing_surfaces_rendered"] = (
            ", ".join(row["missing_surfaces"]) or "-"
        )
        render_row["missing_constraints_rendered"] = (
            ", ".join(row["missing_constraint_surfaces"]) or "-"
        )
        render_row["primary_keys_rendered"] = (
            ", ".join(row["primary_key_fields"]) or "-"
        )
        lines.append(
            "| `{pipeline_name}` | `{dataset_layer}` | `{contract_ref}` | "
            "{gold_enabled} | `{parity_status}` | `{constraint_completeness_status}` | "
            "{gold_strict_validation_declared} | {published_contract_property_count} | "
            "{published_contract_required_count} | {published_contract_check_constraint_count} | "
            "`{primary_keys_rendered}` | {contract_test_count} | {golden_test_count} | "
            "{missing_surfaces_rendered} | {missing_constraints_rendered} |".format(
                **render_row,
                contract_test_count=len(row["contract_test_paths"]),
                golden_test_count=len(row["golden_test_paths"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_artifacts(*, json_out: Path, md_out: Path) -> dict[str, Any]:
    payload = build_payload()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate contract coverage matrix artifacts."
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="JSON output path",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=DEFAULT_MD_OUTPUT,
        help="Markdown output path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed artifacts drift from generator output.",
    )
    args = parser.parse_args(argv)
    snapshot_date = (
        _existing_snapshot_date(args.json_out) if args.check else None
    )

    if args.check:
        expected = json.dumps(
            build_payload(snapshot_date=snapshot_date), indent=2, sort_keys=True
        ) + "\n"
        actual = args.json_out.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "[contract-coverage-matrix] artifact drift detected; regenerate with: "
                "python -m scripts.engineering.qa report-contract-coverage-matrix",
                file=sys.stderr,
            )
            return 1
        print("[ok] contract coverage matrix is up to date")
        return 0

    payload = write_artifacts(json_out=args.json_out, md_out=args.md_out)
    print(
        "[contract-coverage-matrix] "
        f"rows={payload['row_count']}; gold_enabled={payload['gold_enabled_count']}; "
        f"covered={payload['covered_gold_enabled_count']}; "
        f"json={args.json_out}; md={args.md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

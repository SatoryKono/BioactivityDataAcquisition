#!/usr/bin/env python3
"""Validate ontology and unit role separation in semantic surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioetl.infrastructure.config.semantic_field_registry_loader import (  # noqa: E402
    SemanticFieldRegistryLoader,
)

DEFAULT_ROLE_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "ontology_unit_semantic_roles.yaml"
)
DEFAULT_CANONICAL_REGISTRY_ROOT = REPO_ROOT / "configs"
MAPPING_STATUS_VALUES = frozenset({"mapped", "unmapped", "missing"})


@dataclass(frozen=True, slots=True)
class OntologyUnitFinding:
    """One ontology/unit semantic role validation finding."""

    kind: str
    family_id: str
    path: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "family_id": self.family_id,
            "path": self.path,
            "field": self.field,
            "message": self.message,
        }


def _load_yaml(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _repo_path(repo_root: Path, path_value: str) -> Path:
    return repo_root / path_value


def _schema_fields(config: dict[str, Any]) -> set[str]:
    schema = config.get("schema", {})
    groups = schema.get("column_groups", []) if isinstance(schema, dict) else []
    fields: set[str] = set()
    if not isinstance(groups, list):
        return fields
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_fields = group.get("fields", [])
        if not isinstance(group_fields, list):
            continue
        fields.update(field for field in group_fields if isinstance(field, str))
    return fields


def _quality_section(config: dict[str, Any], section: str) -> list[dict[str, Any]]:
    quality = config.get("quality", {})
    values = quality.get(section, []) if isinstance(quality, dict) else []
    return [value for value in values if isinstance(value, dict)]


def _field_validations(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(validation["field"]): validation
        for validation in _quality_section(config, "entity_field_validations")
        if isinstance(validation.get("field"), str)
    }


def _named_quality_entries(
    config: dict[str, Any],
    section: str,
) -> dict[str, dict[str, Any]]:
    return {
        str(entry["name"]): entry
        for entry in _quality_section(config, section)
        if isinstance(entry.get("name"), str)
    }


def _required_filter_fields(config: dict[str, Any], lane: str) -> set[str]:
    filters = config.get("filters", {})
    lane_filters = filters.get(lane, {}) if isinstance(filters, dict) else {}
    fields = (
        lane_filters.get("required_fields", [])
        if isinstance(lane_filters, dict)
        else []
    )
    return {field for field in fields if isinstance(field, str)}


def _role_fields_from_family(family: dict[str, Any]) -> tuple[str, ...]:
    fields: list[str] = []
    role_bindings = family.get("field_roles", {})
    if isinstance(role_bindings, dict):
        fields.extend(
            value for value in role_bindings.values() if isinstance(value, str)
        )
    for key in (
        "code_field",
        "iri_field",
        "mapping_status_field",
        "ontology_version_field",
        "companion_label_field",
    ):
        value = family.get(key)
        if isinstance(value, str):
            fields.append(value)
    return tuple(dict.fromkeys(fields))


def _find_canonicalization_violations(
    *,
    family_id: str,
    path: str,
    fields: tuple[str, ...],
    registry_root: Path,
) -> list[OntologyUnitFinding]:
    registry = SemanticFieldRegistryLoader(registry_root).load()
    findings: list[OntologyUnitFinding] = []
    for field in fields:
        if (
            registry.get_by_canonical_name(field) is not None
            or registry.get_by_legacy_name(field) is not None
            or registry.get_by_raw_provider_name(field) is not None
        ):
            findings.append(
                OntologyUnitFinding(
                    kind="role_field_canonicalized_as_alias_cluster",
                    family_id=family_id,
                    path=path,
                    field=field,
                    message=(
                        f"{family_id} role field {field!r} must remain separate "
                        "from canonical alias clusters"
                    ),
                )
            )
    return findings


def _field_presence_findings(
    *,
    family_id: str,
    path: str,
    required_fields: tuple[str, ...],
    config: dict[str, Any],
) -> list[OntologyUnitFinding]:
    schema_fields = _schema_fields(config)
    return [
        OntologyUnitFinding(
            kind="missing_schema_role_field",
            family_id=family_id,
            path=path,
            field=field,
            message=f"{family_id} role field {field!r} is missing from schema groups",
        )
        for field in required_fields
        if field not in schema_fields
    ]


def _field_validation_findings(
    *,
    family_id: str,
    path: str,
    config: dict[str, Any],
    expected_validations: dict[str, str],
) -> list[OntologyUnitFinding]:
    validations = _field_validations(config)
    findings: list[OntologyUnitFinding] = []
    for field, expected_type in expected_validations.items():
        validation = validations.get(field)
        actual_type = validation.get("type") if validation else None
        if actual_type == expected_type:
            continue
        findings.append(
            OntologyUnitFinding(
                kind="missing_or_wrong_field_validation",
                family_id=family_id,
                path=path,
                field=field,
                message=(
                    f"{family_id} field {field!r} must have {expected_type!r} "
                    f"validation, found {actual_type!r}"
                ),
            )
        )
    return findings


def _cross_field_findings(
    *,
    family_id: str,
    path: str,
    config: dict[str, Any],
    expected_cross_validations: list[dict[str, Any]],
) -> list[OntologyUnitFinding]:
    cross_validations = _named_quality_entries(config, "entity_cross_field_validations")
    findings: list[OntologyUnitFinding] = []
    for expected in expected_cross_validations:
        name = expected.get("name")
        if not isinstance(name, str):
            continue
        actual = cross_validations.get(name)
        if actual is None:
            findings.append(
                OntologyUnitFinding(
                    kind="missing_cross_field_validation",
                    family_id=family_id,
                    path=path,
                    field=name,
                    message=f"{family_id} missing cross-field validation {name!r}",
                )
            )
            continue
        for key in ("condition", "trigger_field", "required_field"):
            expected_value = expected.get(key)
            if expected_value is None or actual.get(key) == expected_value:
                continue
            findings.append(
                OntologyUnitFinding(
                    kind="cross_field_validation_mismatch",
                    family_id=family_id,
                    path=path,
                    field=name,
                    message=(
                        f"{family_id} validation {name!r} expected {key}="
                        f"{expected_value!r}, found {actual.get(key)!r}"
                    ),
                )
            )
        expected_fields = expected.get("fields")
        actual_fields = actual.get("fields", [])
        if isinstance(expected_fields, list) and set(expected_fields) - set(
            actual_fields
        ):
            missing = sorted(set(expected_fields) - set(actual_fields))
            findings.append(
                OntologyUnitFinding(
                    kind="cross_field_validation_missing_fields",
                    family_id=family_id,
                    path=path,
                    field=name,
                    message=f"{family_id} validation {name!r} missing fields {missing}",
                )
            )
    return findings


def _filter_presence_findings(
    *,
    family_id: str,
    path: str,
    config: dict[str, Any],
    lane: str,
    required_fields: list[str],
) -> list[OntologyUnitFinding]:
    present = _required_filter_fields(config, lane)
    return [
        OntologyUnitFinding(
            kind=f"missing_{lane}_required_field",
            family_id=family_id,
            path=path,
            field=field,
            message=f"{family_id} missing {field!r} from filters.{lane}.required_fields",
        )
        for field in required_fields
        if field not in present
    ]


def _ontology_family_findings(
    *,
    repo_root: Path,
    registry_root: Path,
    family: dict[str, Any],
) -> list[OntologyUnitFinding]:
    family_id = str(family.get("family_id") or "<unknown>")
    path = str(family.get("path") or "")
    config = _load_yaml(_repo_path(repo_root, path))
    fields = _role_fields_from_family(family)
    findings: list[OntologyUnitFinding] = []
    findings.extend(
        _find_canonicalization_violations(
            family_id=family_id,
            path=path,
            fields=fields,
            registry_root=registry_root,
        )
    )
    findings.extend(
        _field_presence_findings(
            family_id=family_id,
            path=path,
            required_fields=fields,
            config=config,
        )
    )

    expected_validations: dict[str, str] = {
        str(family["mapping_status_field"]): "enum",
        str(family["iri_field"]): "pattern",
    }
    code_validation_type = family.get("required_code_validation_type")
    if isinstance(code_validation_type, str) and isinstance(
        family.get("code_field"), str
    ):
        expected_validations[str(family["code_field"])] = code_validation_type
    findings.extend(
        _field_validation_findings(
            family_id=family_id,
            path=path,
            config=config,
            expected_validations=expected_validations,
        )
    )

    validations = _field_validations(config)
    mapping_status_field = str(family.get("mapping_status_field") or "")
    mapping_status_validation = validations.get(mapping_status_field, {})
    allowed_values = set(mapping_status_validation.get("allowed", []))
    if not MAPPING_STATUS_VALUES <= allowed_values:
        findings.append(
            OntologyUnitFinding(
                kind="mapping_status_enum_mismatch",
                family_id=family_id,
                path=path,
                field=mapping_status_field,
                message=(
                    f"{family_id} mapping status must allow "
                    f"{sorted(MAPPING_STATUS_VALUES)}, found {sorted(allowed_values)}"
                ),
            )
        )

    cross_name = str(family.get("required_cross_field_validation") or "")
    findings.extend(
        _cross_field_findings(
            family_id=family_id,
            path=path,
            config=config,
            expected_cross_validations=[
                {
                    "name": cross_name,
                    "condition": "conditional_required",
                    "trigger_field": family.get("code_field"),
                    "required_field": family.get("mapping_status_field"),
                }
            ],
        )
    )

    conditional_name = str(family.get("required_conditional_validation") or "")
    conditional_validations = _named_quality_entries(
        config, "entity_conditional_validations"
    )
    conditional = conditional_validations.get(conditional_name)
    if conditional is None:
        findings.append(
            OntologyUnitFinding(
                kind="missing_conditional_validation",
                family_id=family_id,
                path=path,
                field=conditional_name,
                message=f"{family_id} missing conditional validation {conditional_name!r}",
            )
        )
        return findings

    if conditional.get("condition_field") != mapping_status_field:
        findings.append(
            OntologyUnitFinding(
                kind="conditional_validation_condition_field_mismatch",
                family_id=family_id,
                path=path,
                field=conditional_name,
                message=(
                    f"{family_id} conditional {conditional_name!r} must be keyed "
                    f"by {mapping_status_field!r}"
                ),
            )
        )
    if conditional.get("condition_value") != "mapped":
        findings.append(
            OntologyUnitFinding(
                kind="conditional_validation_condition_value_mismatch",
                family_id=family_id,
                path=path,
                field=conditional_name,
                message=f"{family_id} conditional {conditional_name!r} must key on mapped",
            )
        )

    then_validations = conditional.get("then_validations", [])
    required_then_fields = {
        str(family.get("iri_field") or ""),
        str(family.get("ontology_version_field") or ""),
    }
    actual_then_fields = {
        str(item.get("field"))
        for item in then_validations
        if isinstance(item, dict) and item.get("type") == "required"
    }
    missing_then_fields = sorted(required_then_fields - actual_then_fields)
    if missing_then_fields:
        findings.append(
            OntologyUnitFinding(
                kind="conditional_validation_missing_required_bundle_fields",
                family_id=family_id,
                path=path,
                field=conditional_name,
                message=(
                    f"{family_id} conditional {conditional_name!r} missing required "
                    f"bundle fields {missing_then_fields}"
                ),
            )
        )
    return findings


def _measurement_family_findings(
    *,
    repo_root: Path,
    registry_root: Path,
    family: dict[str, Any],
) -> list[OntologyUnitFinding]:
    family_id = str(family.get("family_id") or "<unknown>")
    path = str(family.get("path") or "")
    config = _load_yaml(_repo_path(repo_root, path))
    fields = _role_fields_from_family(family)
    findings: list[OntologyUnitFinding] = []
    findings.extend(
        _find_canonicalization_violations(
            family_id=family_id,
            path=path,
            fields=fields,
            registry_root=registry_root,
        )
    )
    findings.extend(
        _field_presence_findings(
            family_id=family_id,
            path=path,
            required_fields=fields,
            config=config,
        )
    )

    expected_validations = family.get("required_field_validations", {})
    if isinstance(expected_validations, dict):
        findings.extend(
            _field_validation_findings(
                family_id=family_id,
                path=path,
                config=config,
                expected_validations={
                    str(field): str(validation_type)
                    for field, validation_type in expected_validations.items()
                },
            )
        )

    expected_cross = family.get("required_cross_field_validations", [])
    if isinstance(expected_cross, list):
        findings.extend(
            _cross_field_findings(
                family_id=family_id,
                path=path,
                config=config,
                expected_cross_validations=[
                    entry for entry in expected_cross if isinstance(entry, dict)
                ],
            )
        )

    silver_fields = family.get("required_silver_fields", [])
    if isinstance(silver_fields, list):
        findings.extend(
            _filter_presence_findings(
                family_id=family_id,
                path=path,
                config=config,
                lane="silver_filters",
                required_fields=[
                    field for field in silver_fields if isinstance(field, str)
                ],
            )
        )
    gold_fields = family.get("required_gold_fields", [])
    if isinstance(gold_fields, list):
        findings.extend(
            _filter_presence_findings(
                family_id=family_id,
                path=path,
                config=config,
                lane="gold_filters",
                required_fields=[
                    field for field in gold_fields if isinstance(field, str)
                ],
            )
        )
    return findings


def validate_ontology_unit_semantics(
    *,
    repo_root: Path = REPO_ROOT,
    role_registry_path: Path = DEFAULT_ROLE_REGISTRY,
    canonical_registry_root: Path = DEFAULT_CANONICAL_REGISTRY_ROOT,
) -> tuple[OntologyUnitFinding, ...]:
    """Return ontology/unit semantic role findings."""
    role_registry = _load_yaml(role_registry_path)
    findings: list[OntologyUnitFinding] = []

    measurement_families = role_registry.get("measurement_role_families", [])
    if isinstance(measurement_families, list):
        for family in measurement_families:
            if isinstance(family, dict):
                findings.extend(
                    _measurement_family_findings(
                        repo_root=repo_root,
                        registry_root=canonical_registry_root,
                        family=family,
                    )
                )

    ontology_families = role_registry.get("ontology_role_families", [])
    if isinstance(ontology_families, list):
        for family in ontology_families:
            if isinstance(family, dict):
                findings.extend(
                    _ontology_family_findings(
                        repo_root=repo_root,
                        registry_root=canonical_registry_root,
                        family=family,
                    )
                )
    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate ontology and unit role separation in semantic surfaces.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing configs and field registries",
    )
    parser.add_argument(
        "--role-registry",
        type=Path,
        default=DEFAULT_ROLE_REGISTRY,
        help="ontology/unit semantic role registry",
    )
    parser.add_argument(
        "--canonical-registry-root",
        type=Path,
        default=DEFAULT_CANONICAL_REGISTRY_ROOT,
        help="configs root containing field_registry/canonical_registry.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    findings = validate_ontology_unit_semantics(
        repo_root=args.repo_root,
        role_registry_path=args.role_registry,
        canonical_registry_root=args.canonical_registry_root,
    )
    if args.json:
        payload = {
            "ok": not findings,
            "finding_count": len(findings),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("[ontology-unit-semantics] validation failed")
        for finding in findings:
            print(f"- {finding.message}")
    else:
        print("[ontology-unit-semantics] ok")

    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

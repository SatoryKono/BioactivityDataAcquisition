#!/usr/bin/env python3
"""Export deterministic observed vocabulary rows from tracked ChEMBL Bronze fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from bioetl.domain.normalization.profiles import resolve_normalization_profile
from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    chembl_policy_surface,
)
from bioetl.domain.schemas._chembl_enum_catalog import CHEMBL_ENUM_CATALOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
ONTOLOGY_PATH = PROJECT_ROOT / "configs" / "vocab" / "chembl_ontology.yaml"
DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "reports" / "generated"
DEFAULT_CSV_OUT = DEFAULT_OUT_DIR / "chembl_observed_vocab_inventory.csv"
DEFAULT_JSON_OUT = DEFAULT_OUT_DIR / "chembl_observed_vocab_inventory.json"


@dataclass(frozen=True, slots=True)
class ObservedVocabRow:
    pipeline_name: str
    fixture_key: str
    field_name: str
    layer_hint: str
    observed_value: str
    count: int
    normalized_value: str
    classification_hint: str
    fixture_path: str

    def as_dict(self) -> dict[str, object]:
        return {
            "pipeline_name": self.pipeline_name,
            "fixture_key": self.fixture_key,
            "field_name": self.field_name,
            "layer_hint": self.layer_hint,
            "observed_value": self.observed_value,
            "count": self.count,
            "normalized_value": self.normalized_value,
            "classification_hint": self.classification_hint,
            "fixture_path": self.fixture_path,
        }


@dataclass(frozen=True, slots=True)
class TrackedFixtureSource:
    fixture_key: str
    fixture_path: str
    layer_hint: str


@dataclass(frozen=True, slots=True)
class GovernedFieldCoverage:
    pipeline_name: str
    fixture_key: str
    field_name: str
    classification_hint: str
    fixture_paths: tuple[str, ...]
    raw_field_present: bool
    observed_distinct_count: int
    normalized_distinct_count: int
    observed_examples: tuple[str, ...]
    normalized_examples: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "pipeline_name": self.pipeline_name,
            "fixture_key": self.fixture_key,
            "field_name": self.field_name,
            "classification_hint": self.classification_hint,
            "fixture_paths": list(self.fixture_paths),
            "raw_field_present": self.raw_field_present,
            "observed_distinct_count": self.observed_distinct_count,
            "normalized_distinct_count": self.normalized_distinct_count,
            "observed_examples": list(self.observed_examples),
            "normalized_examples": list(self.normalized_examples),
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} must decode to a mapping"
    return payload


def _tracked_fixture_sources() -> list[TrackedFixtureSource]:
    fixtures = _load_yaml(MANIFEST_PATH).get("fixtures", {})
    assert isinstance(fixtures, dict)
    entries: list[TrackedFixtureSource] = []
    for fixture_key, entry in fixtures.items():
        if (
            not isinstance(fixture_key, str)
            or not fixture_key.startswith("chembl/")
            or not isinstance(entry, dict)
            or entry.get("fixture_kind") != "tracked_ci_sample"
        ):
            continue
        fixture_path = entry.get("fixture_path")
        assert isinstance(fixture_path, str), f"{fixture_key}: fixture_path missing"
        entries.append(
            TrackedFixtureSource(
                fixture_key=fixture_key,
                fixture_path=fixture_path,
                layer_hint="bronze_fixture",
            )
        )
        edge_fixtures = entry.get("edge_fixtures") or []
        assert isinstance(edge_fixtures, list), (
            f"{fixture_key}: edge_fixtures must be a list when present"
        )
        for edge_fixture in edge_fixtures:
            if not isinstance(edge_fixture, dict):
                continue
            edge_path = edge_fixture.get("fixture_path")
            if not isinstance(edge_path, str):
                continue
            entries.append(
                TrackedFixtureSource(
                    fixture_key=fixture_key,
                    fixture_path=edge_path,
                    layer_hint="edge_fixture",
                )
            )
    return sorted(entries, key=lambda item: (item.fixture_key, item.fixture_path))


def _pipeline_name_from_fixture_key(fixture_key: str) -> str:
    provider, entity = fixture_key.split("/", maxsplit=1)
    return f"{provider}_{entity}"


def _canonical_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        assert isinstance(payload, dict), f"{path} rows must be JSON objects"
        rows.append(payload)
    return rows


def _parse_pipeline_field_ref(field_ref: object) -> tuple[str, str] | None:
    if not isinstance(field_ref, str) or "." not in field_ref:
        return None
    pipeline_name, field_name = field_ref.split(".", maxsplit=1)
    return pipeline_name, field_name


def _register_ontology_family_fields(
    result: dict[tuple[str, str], str],
    families: object,
) -> None:
    if not isinstance(families, dict):
        return
    for family_name, family_payload in families.items():
        if not isinstance(family_payload, dict):
            continue
        for field_ref in family_payload.get("fields", []):
            parsed = _parse_pipeline_field_ref(field_ref)
            if parsed is None:
                continue
            result[parsed] = f"ontology:{family_name}"


def _register_unit_policy_fields(
    result: dict[tuple[str, str], str],
    unit_policies: object,
) -> None:
    if not isinstance(unit_policies, dict):
        return
    for policy_payload in unit_policies.values():
        if not isinstance(policy_payload, dict):
            continue
        for field_ref in policy_payload.get("fields", []):
            parsed = _parse_pipeline_field_ref(field_ref)
            if parsed is None:
                continue
            result.setdefault(parsed, "unit_boundary")


def _ontology_field_map() -> dict[tuple[str, str], str]:
    payload = _load_yaml(ONTOLOGY_PATH)
    result: dict[tuple[str, str], str] = {}
    families = payload.get("families", {})
    assert isinstance(families, dict)
    _register_ontology_family_fields(result, families)
    _register_unit_policy_fields(result, payload.get("unit_companion_policies", {}))
    return result


def _classification_hint(
    pipeline_name: str,
    entity_type: str,
    field_name: str,
    *,
    ontology_fields: dict[tuple[str, str], str],
) -> str | None:
    if (entity_type, field_name) in CHEMBL_ENUM_CATALOG:
        return "enum"
    ontology_hint = ontology_fields.get((pipeline_name, field_name))
    if ontology_hint is not None:
        return ontology_hint
    profile = resolve_normalization_profile("chembl", entity_type)
    if profile is None:
        return None
    field_identity = profile.field_identity(field_name)
    if field_identity is None:
        return None
    if field_identity.normalizer_ref.endswith(":_identity"):
        return None
    return "normalized_field"


def _governed_field_classification(
    pipeline_name: str,
    entity_type: str,
    field_name: str,
    *,
    ontology_fields: dict[tuple[str, str], str],
) -> str | None:
    if (entity_type, field_name) in CHEMBL_ENUM_CATALOG:
        return "enum"
    ontology_hint = ontology_fields.get((pipeline_name, field_name))
    if ontology_hint is not None:
        return ontology_hint
    policy_surface = chembl_policy_surface(entity_type, field_name)
    if policy_surface is None:
        return None
    if policy_surface.category == "reference_identifier":
        return "reference_identifier"
    if policy_surface.category == "derived_vocabulary":
        return "derived_vocabulary"
    return policy_surface.category


def _governed_profile_fields(
    pipeline_name: str,
    entity_type: str,
    *,
    ontology_fields: dict[tuple[str, str], str],
) -> dict[str, str]:
    profile = resolve_normalization_profile("chembl", entity_type)
    if profile is None:
        return {}
    governed: dict[str, str] = {}
    for field_name in sorted(profile.fields):
        classification = _governed_field_classification(
            pipeline_name,
            entity_type,
            field_name,
            ontology_fields=ontology_fields,
        )
        if classification is not None:
            governed[field_name] = classification
    return governed


def _init_governed_field_state(
    *,
    pipeline_name: str,
    fixture_key: str,
    field_name: str,
    classification: str,
) -> dict[str, object]:
    return {
        "pipeline_name": pipeline_name,
        "fixture_key": fixture_key,
        "field_name": field_name,
        "classification_hint": classification,
        "fixture_paths": set(),
        "raw_field_present": False,
        "observed_values": set(),
        "normalized_values": set(),
    }


def _register_governed_fields_for_fixture(
    governed_field_states: dict[tuple[str, str], dict[str, object]],
    *,
    pipeline_name: str,
    fixture_key: str,
    fixture_path_raw: str,
    governed_fields: dict[str, str],
) -> None:
    for field_name, classification in governed_fields.items():
        state = governed_field_states.setdefault(
            (pipeline_name, field_name),
            _init_governed_field_state(
                pipeline_name=pipeline_name,
                fixture_key=fixture_key,
                field_name=field_name,
                classification=classification,
            ),
        )
        cast_fixture_paths = state["fixture_paths"]
        assert isinstance(cast_fixture_paths, set)
        cast_fixture_paths.add(fixture_path_raw)


def _normalized_field_value(
    profile: Any,
    field_name: str,
    value: object,
    record: dict[str, Any],
) -> str:
    normalized_value_obj = (
        profile.rule_for(field_name).apply(value, record=record)
        if profile is not None and profile.rule_for(field_name) is not None
        else value
    )
    if normalized_value_obj is None:
        return ""
    return _canonical_value(normalized_value_obj)


def _record_governed_observation(
    governed_state: dict[str, object] | None,
    *,
    observed_value: str,
    normalized_value: str,
) -> None:
    if governed_state is None:
        return
    governed_state["raw_field_present"] = True
    observed_values = governed_state["observed_values"]
    normalized_values = governed_state["normalized_values"]
    assert isinstance(observed_values, set)
    assert isinstance(normalized_values, set)
    observed_values.add(observed_value)
    if normalized_value:
        normalized_values.add(normalized_value)


def _count_fixture_field_values(
    *,
    fixture_path: Path,
    pipeline_name: str,
    entity_type: str,
    profile: Any,
    ontology_fields: dict[tuple[str, str], str],
    governed_field_states: dict[tuple[str, str], dict[str, object]],
) -> dict[tuple[str, str, str], Counter[str]]:
    field_counters: dict[tuple[str, str, str], Counter[str]] = {}
    for record in _load_jsonl(fixture_path):
        for field_name, value in record.items():
            if value is None:
                continue
            classification = _classification_hint(
                pipeline_name,
                entity_type,
                field_name,
                ontology_fields=ontology_fields,
            )
            if classification is None:
                continue
            observed_value = _canonical_value(value)
            normalized_value = _normalized_field_value(
                profile, field_name, value, record
            )
            counter_key = (field_name, classification, normalized_value)
            field_counters.setdefault(counter_key, Counter())[observed_value] += 1
            _record_governed_observation(
                governed_field_states.get((pipeline_name, field_name)),
                observed_value=observed_value,
                normalized_value=normalized_value,
            )
    return field_counters


def _observed_rows_from_counters(
    *,
    field_counters: dict[tuple[str, str, str], Counter[str]],
    pipeline_name: str,
    fixture_key: str,
    layer_hint: str,
    fixture_path_raw: str,
) -> list[ObservedVocabRow]:
    rows: list[ObservedVocabRow] = []
    for (field_name, classification, normalized_value), counter in sorted(
        field_counters.items()
    ):
        for observed_value, count in sorted(counter.items()):
            rows.append(
                ObservedVocabRow(
                    pipeline_name=pipeline_name,
                    fixture_key=fixture_key,
                    field_name=field_name,
                    layer_hint=layer_hint,
                    observed_value=observed_value,
                    count=count,
                    normalized_value=normalized_value,
                    classification_hint=classification,
                    fixture_path=fixture_path_raw,
                )
            )
    return rows


def build_inventory_payload() -> dict[str, object]:
    ontology_fields = _ontology_field_map()
    rows: list[ObservedVocabRow] = []
    scanned_pipelines: set[str] = set()
    governed_field_states: dict[
        tuple[str, str],
        dict[str, object],
    ] = {}

    for fixture_source in _tracked_fixture_sources():
        fixture_key = fixture_source.fixture_key
        fixture_path_raw = fixture_source.fixture_path
        fixture_path = PROJECT_ROOT / fixture_path_raw
        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Missing declared fixture path: {fixture_path_raw}"
            )

        pipeline_name = _pipeline_name_from_fixture_key(fixture_key)
        entity_type = fixture_key.split("/", maxsplit=1)[1]
        profile = resolve_normalization_profile("chembl", entity_type)
        scanned_pipelines.add(pipeline_name)
        governed_fields = _governed_profile_fields(
            pipeline_name,
            entity_type,
            ontology_fields=ontology_fields,
        )
        _register_governed_fields_for_fixture(
            governed_field_states,
            pipeline_name=pipeline_name,
            fixture_key=fixture_key,
            fixture_path_raw=fixture_path_raw,
            governed_fields=governed_fields,
        )
        field_counters = _count_fixture_field_values(
            fixture_path=fixture_path,
            pipeline_name=pipeline_name,
            entity_type=entity_type,
            profile=profile,
            ontology_fields=ontology_fields,
            governed_field_states=governed_field_states,
        )
        rows.extend(
            _observed_rows_from_counters(
                field_counters=field_counters,
                pipeline_name=pipeline_name,
                fixture_key=fixture_key,
                layer_hint=fixture_source.layer_hint,
                fixture_path_raw=fixture_path_raw,
            )
        )

    rows.sort(
        key=lambda row: (
            row.pipeline_name,
            row.field_name,
            row.fixture_path,
            row.normalized_value,
            row.observed_value,
        )
    )
    governed_fields = [
        GovernedFieldCoverage(
            pipeline_name=str(state["pipeline_name"]),
            fixture_key=str(state["fixture_key"]),
            field_name=str(state["field_name"]),
            classification_hint=str(state["classification_hint"]),
            fixture_paths=tuple(sorted(_state_string_set(state, "fixture_paths"))),
            raw_field_present=bool(state["raw_field_present"]),
            observed_distinct_count=len(_state_string_set(state, "observed_values")),
            normalized_distinct_count=len(_state_string_set(state, "normalized_values")),
            observed_examples=tuple(
                sorted(_state_string_set(state, "observed_values"))[:10]
            ),
            normalized_examples=tuple(
                sorted(_state_string_set(state, "normalized_values"))[:10]
            ),
        )
        for _, state in sorted(governed_field_states.items())
    ]
    return {
        "source": "tracked_chembl_bronze_fixtures",
        "manifest_path": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "pipelines_scanned": sorted(scanned_pipelines),
        "governed_fields_count": len(governed_fields),
        "governed_fields_with_observations_count": sum(
            1 for field in governed_fields if field.raw_field_present
        ),
        "governed_fields_missing_from_fixtures_count": sum(
            1 for field in governed_fields if not field.raw_field_present
        ),
        "governed_fields": [field.as_dict() for field in governed_fields],
        "rows_count": len(rows),
        "rows": [row.as_dict() for row in rows],
    }


def _state_string_set(state: dict[str, object], key: str) -> set[str]:
    """Return stringified members from one governed-field state collection."""
    value = state.get(key)
    if not isinstance(value, (list, tuple, set, frozenset)):
        return set()
    return {str(item) for item in value}


def _render_csv(rows: list[dict[str, object]]) -> str:
    buffer = StringIO(newline="")
    fieldnames = [
        "pipeline_name",
        "fixture_key",
        "field_name",
        "layer_hint",
        "observed_value",
        "count",
        "normalized_value",
        "classification_hint",
        "fixture_path",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _write(path: Path, content: str) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    payload = build_inventory_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    csv_payload = _render_csv(rows)
    json_payload = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if args.check:
        existing_csv = args.csv_out.read_text(encoding="utf-8")
        existing_json = args.json_out.read_text(encoding="utf-8")
        if existing_csv != csv_payload or existing_json != json_payload:
            return 1
        return 0

    _write(args.csv_out, csv_payload)
    _write(args.json_out, json_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} must decode to a mapping"
    return payload


def _tracked_fixture_entries() -> list[tuple[str, dict[str, Any]]]:
    fixtures = _load_yaml(MANIFEST_PATH).get("fixtures", {})
    assert isinstance(fixtures, dict)
    entries = [
        (fixture_key, entry)
        for fixture_key, entry in fixtures.items()
        if isinstance(fixture_key, str)
        and fixture_key.startswith("chembl/")
        and isinstance(entry, dict)
        and entry.get("fixture_kind") == "tracked_ci_sample"
    ]
    return sorted(entries, key=lambda item: item[0])


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


def _ontology_field_map() -> dict[tuple[str, str], str]:
    payload = _load_yaml(ONTOLOGY_PATH)
    result: dict[tuple[str, str], str] = {}
    families = payload.get("families", {})
    assert isinstance(families, dict)
    for family_name, family_payload in families.items():
        if not isinstance(family_payload, dict):
            continue
        for field_ref in family_payload.get("fields", []):
            if not isinstance(field_ref, str) or "." not in field_ref:
                continue
            pipeline_name, field_name = field_ref.split(".", maxsplit=1)
            result[(pipeline_name, field_name)] = f"ontology:{family_name}"
    unit_policies = payload.get("unit_companion_policies", {})
    if isinstance(unit_policies, dict):
        for policy_payload in unit_policies.values():
            if not isinstance(policy_payload, dict):
                continue
            for field_ref in policy_payload.get("fields", []):
                if not isinstance(field_ref, str) or "." not in field_ref:
                    continue
                pipeline_name, field_name = field_ref.split(".", maxsplit=1)
                result.setdefault(
                    (pipeline_name, field_name),
                    "unit_boundary",
                )
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


def build_inventory_payload() -> dict[str, object]:
    ontology_fields = _ontology_field_map()
    rows: list[ObservedVocabRow] = []
    scanned_pipelines: list[str] = []

    for fixture_key, entry in _tracked_fixture_entries():
        fixture_path_raw = entry.get("fixture_path")
        assert isinstance(fixture_path_raw, str), f"{fixture_key}: fixture_path missing"
        fixture_path = PROJECT_ROOT / fixture_path_raw
        if not fixture_path.exists():
            raise FileNotFoundError(f"Missing declared fixture path: {fixture_path_raw}")

        pipeline_name = _pipeline_name_from_fixture_key(fixture_key)
        entity_type = fixture_key.split("/", maxsplit=1)[1]
        profile = resolve_normalization_profile("chembl", entity_type)
        scanned_pipelines.append(pipeline_name)

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
                normalized_value_obj = (
                    profile.rule_for(field_name).apply(value, record=record)
                    if profile is not None and profile.rule_for(field_name) is not None
                    else value
                )
                normalized_value = (
                    "" if normalized_value_obj is None else _canonical_value(normalized_value_obj)
                )
                counter_key = (field_name, classification, normalized_value)
                field_counters.setdefault(counter_key, Counter())[observed_value] += 1

        for (field_name, classification, normalized_value), counter in sorted(
            field_counters.items()
        ):
            for observed_value, count in sorted(counter.items()):
                rows.append(
                    ObservedVocabRow(
                        pipeline_name=pipeline_name,
                        fixture_key=fixture_key,
                        field_name=field_name,
                        layer_hint="bronze_fixture",
                        observed_value=observed_value,
                        count=count,
                        normalized_value=normalized_value,
                        classification_hint=classification,
                        fixture_path=fixture_path_raw,
                    )
                )

    rows.sort(
        key=lambda row: (
            row.pipeline_name,
            row.field_name,
            row.normalized_value,
            row.observed_value,
        )
    )
    return {
        "source": "tracked_chembl_bronze_fixtures",
        "manifest_path": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "pipelines_scanned": sorted(scanned_pipelines),
        "rows_count": len(rows),
        "rows": [row.as_dict() for row in rows],
    }


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

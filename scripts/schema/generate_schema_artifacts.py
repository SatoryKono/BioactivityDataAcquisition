#!/usr/bin/env python3
"""Generate schema artifacts from canonical unified entity schema sections.

Artifacts:
- Pandera silver registry: src/bioetl/domain/schemas/generated/registry.py
- Gold JSON contracts: docs/04-reference/contracts/gold/*.json

Usage:
    python -m scripts.schema generate-artifacts
    python -m scripts.schema generate-artifacts --check
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DIR = PROJECT_ROOT / "configs" / "entities"
COMPOSITES_DIR = PROJECT_ROOT / "configs" / "composites"
PANDERA_REGISTRY_PATH = (
    PROJECT_ROOT / "src" / "bioetl" / "domain" / "schemas" / "generated" / "registry.py"
)
GENERATED_GLOB = "docs/04-reference/contracts/gold/*.json"
GENERATED_CONTRACTS_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"


@dataclass(frozen=True)
class CanonicalSchemaEntry:
    """Canonical schema mapping for provider/entity pair."""

    provider: str
    entity: str
    yaml_path: str
    column_groups: tuple[str, ...]


def _iter_canonical_schema_files() -> list[Path]:
    files: list[Path] = []
    for yaml_path in sorted(CANONICAL_DIR.rglob("*.yaml")):
        if yaml_path.name.startswith("_"):
            continue
        rel = yaml_path.relative_to(CANONICAL_DIR)
        if len(rel.parts) < 2 or rel.parts[0] == "field_groups":
            continue
        if rel.parts[0] == "composite":
            continue
        files.append(yaml_path)
    for yaml_path in sorted(COMPOSITES_DIR.rglob("*.yaml")):
        if yaml_path.name.startswith("_"):
            continue
        rel = yaml_path.relative_to(COMPOSITES_DIR)
        if len(rel.parts) > 1:
            continue
        files.append(yaml_path)
    return files


def _column_groups_from_mapping(payload: object, *keys: str) -> list[object]:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key, {})
    if isinstance(current, list):
        return current
    return []


def _load_composite_entry_parts(
    yaml_path: Path, payload_dict: dict[str, object]
) -> tuple[str, Path, str, list[object]]:
    rel = yaml_path.relative_to(COMPOSITES_DIR)
    groups = _column_groups_from_mapping(payload_dict, "composite", "schema", "column_groups")
    if not groups:
        groups = _column_groups_from_mapping(
            payload_dict, "composite", "merge", "column_groups"
        )
    return "composite", rel, f"composite/{rel.as_posix()}", groups


def _load_entity_entry_parts(
    yaml_path: Path, payload_dict: dict[str, object]
) -> tuple[str, Path, str, list[object]]:
    rel = yaml_path.relative_to(CANONICAL_DIR)
    groups = _column_groups_from_mapping(payload_dict, "schema", "column_groups")
    return rel.parts[0], rel, rel.as_posix(), groups


def _load_entry(yaml_path: Path) -> CanonicalSchemaEntry:
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    payload_dict = payload if isinstance(payload, dict) else {}
    if COMPOSITES_DIR in yaml_path.parents:
        provider, rel, yaml_path_value, groups = _load_composite_entry_parts(
            yaml_path, payload_dict
        )
    else:
        provider, rel, yaml_path_value, groups = _load_entity_entry_parts(
            yaml_path, payload_dict
        )
    group_names = [
        str(group["name"])
        for group in groups
        if isinstance(group, dict) and "name" in group
    ]
    return CanonicalSchemaEntry(
        provider=provider,
        entity=rel.stem,
        yaml_path=yaml_path_value,
        column_groups=tuple(group_names),
    )


def _build_registry(entries: list[CanonicalSchemaEntry]) -> str:
    lines: list[str] = []
    lines.append('"""Auto-generated registry from configs/entities schema sections.')
    lines.append("")
    lines.append(
        "DO NOT EDIT MANUALLY. Run: python -m scripts.schema generate-artifacts"
    )
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from dataclasses import dataclass")
    lines.append("")
    lines.append("")
    lines.append("@dataclass(frozen=True)")
    lines.append("class CanonicalSchemaRegistryEntry:")
    lines.append('    """Entry in the canonical schema registry."""')
    lines.append("")
    lines.append("    provider: str")
    lines.append("    entity: str")
    lines.append("    yaml_path: str")
    lines.append("    column_groups: tuple[str, ...]")
    lines.append("")
    lines.append("")
    lines.append(
        "_RAW_CANONICAL_SCHEMA_REGISTRY: tuple[tuple[str, str, str, tuple[str, ...]], ...] = ("
    )
    for entry in entries:
        group_values = ", ".join(f'"{group}"' for group in entry.column_groups)
        group_suffix = "," if len(entry.column_groups) == 1 else ""
        lines.append(
            f'    ("{entry.provider}", "{entry.entity}", "{entry.yaml_path}", ({group_values}{group_suffix})),'
        )
    lines.append(")")
    lines.append("")
    lines.append(
        "CANONICAL_SCHEMA_REGISTRY: tuple[CanonicalSchemaRegistryEntry, ...] = ("
    )
    lines.append("    tuple(")
    lines.append("        CanonicalSchemaRegistryEntry(")
    lines.append("            provider=provider,")
    lines.append("            entity=entity,")
    lines.append("            yaml_path=yaml_path,")
    lines.append("            column_groups=column_groups,")
    lines.append("        )")
    lines.append(
        "        for provider, entity, yaml_path, column_groups in _RAW_CANONICAL_SCHEMA_REGISTRY"
    )
    lines.append("    )")
    lines.append(")")
    lines.append("")
    lines.append(
        '__all__ = ["CANONICAL_SCHEMA_REGISTRY", "CanonicalSchemaRegistryEntry"]'
    )
    lines.append("")
    return "\n".join(lines)


def _emit(message: str, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    stream.write(f"{message}\n")


def _ruff_format(content: str) -> str:
    """Run ruff format on generated content to ensure compliance."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--stdin-filename",
            "registry.py",
            "-",
        ],
        input=content,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    return content


def _write_if_changed(path: Path, content: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        _emit(f"OK    {path.relative_to(PROJECT_ROOT)}")
        return False
    if check:
        _emit(f"STALE {path.relative_to(PROJECT_ROOT)}", err=True)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _emit(f"WROTE {path.relative_to(PROJECT_ROOT)}")
    return False


def _run_gold_contract_generation(check: bool) -> bool:
    if check:
        current = _snapshot_generated_contracts()
        expected = _expected_generated_contracts_snapshot()
        stale = current != expected
        if stale:
            _emit(f"STALE {GENERATED_GLOB}", err=True)
        return stale

    before = _snapshot_generated_contracts()
    subprocess.run(
        [sys.executable, "-m", "scripts.schema.generate_contracts"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    after = _snapshot_generated_contracts()
    stale = before != after
    if stale and check:
        _emit(f"STALE {GENERATED_GLOB}", err=True)
    return stale


def _snapshot_generated_contracts() -> dict[str, str]:
    """Read generated contract files into a deterministic snapshot."""
    snapshot: dict[str, str] = {}
    for path in sorted(GENERATED_CONTRACTS_DIR.glob("*.json")):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        snapshot[rel] = path.read_text(encoding="utf-8")
    return snapshot


def _load_generate_contracts_module() -> ModuleType:
    """Load the contract generator through its package module path."""
    return importlib.import_module("scripts.schema.generate_contracts")


def _expected_generated_contracts_snapshot() -> dict[str, str]:
    """Build the expected Gold contract snapshot without mutating the workspace."""
    module = _load_generate_contracts_module()
    schema_classes: list[type[object]] = []
    for export_name in module.gold_contracts.__all__:
        export_obj = getattr(module.gold_contracts, export_name)
        if inspect.isclass(export_obj) and export_name.endswith("GoldSchema"):
            schema_classes.append(export_obj)

    schema_classes.sort(key=lambda cls: cls.__name__)
    snapshot: dict[str, str] = {}

    for schema_cls in schema_classes:
        entity = module._class_to_entity(schema_cls.__name__)
        contract_version = module._contract_version_for_entity(entity)
        filename = module._filename_from_version(entity, contract_version)
        output_path = GENERATED_CONTRACTS_DIR / filename
        contract = module._build_contract(schema_cls, entity, contract_version)
        snapshot[output_path.relative_to(PROJECT_ROOT).as_posix()] = (
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
        )

    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate schema artifacts")
    parser.add_argument(
        "--check", action="store_true", help="Fail if artifacts are stale"
    )
    args = parser.parse_args()

    entries = [_load_entry(path) for path in _iter_canonical_schema_files()]
    registry_content = _ruff_format(_build_registry(entries))
    stale_registry = _write_if_changed(
        PANDERA_REGISTRY_PATH, registry_content, args.check
    )
    stale_contracts = _run_gold_contract_generation(args.check)

    if args.check and (stale_registry or stale_contracts):
        _emit(
            "\nGenerated artifacts are stale. Run: python -m scripts.schema generate-artifacts",
            err=True,
        )
        return 1

    _emit("\nSchema artifact generation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

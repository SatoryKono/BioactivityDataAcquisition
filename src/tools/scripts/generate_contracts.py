#!/usr/bin/env python3
"""Export Gold layer JSON Schema contracts to docs/04-reference/contracts/gold/."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

CONTRACTS_DIR = REPO_ROOT / "docs" / "04-reference" / "contracts" / "gold"
SCHEMA_VERSION = "v1.0"
PREFIX_MAP: list[tuple[str, str]] = [
    ("ChEMBL", "chembl"),
    ("PubChem", "pubchem"),
    ("UniProt", "uniprot"),
    ("PubMed", "pubmed"),
    ("CrossRef", "crossref"),
    ("OpenAlex", "openalex"),
    ("SemanticScholar", "semanticscholar"),
    ("Composite", "composite"),
]


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value).lower()


def _class_name_to_entity(schema_name: str) -> str:
    """Convert schema class names to contract entity IDs."""
    base_name = schema_name.removesuffix("GoldSchema")
    for prefix, normalized in PREFIX_MAP:
        if base_name.startswith(prefix):
            tail = base_name[len(prefix) :]
            return f"{normalized}_{_camel_to_snake(tail)}".strip("_")
    return _camel_to_snake(base_name)


def _make_deterministic(value: Any, *, key: str | None = None) -> Any:
    """Recursively normalize schema objects for deterministic JSON output."""
    if isinstance(value, dict):
        return {k: _make_deterministic(v, key=k) for k, v in sorted(value.items())}

    if isinstance(value, list):
        normalized = [_make_deterministic(item, key=key) for item in value]
        if key in {"required", "enum"} and all(
            isinstance(item, str) for item in normalized
        ):
            return sorted(normalized)
        return normalized

    return value


def _get_gold_schemas() -> list[tuple[str, type[Any]]]:
    """Load schema classes from bioetl.domain.contracts.gold using module __all__."""
    from bioetl.domain.contracts import gold

    schemas: list[tuple[str, type[Any]]] = []
    for exported_name in sorted(gold.__all__):
        exported = getattr(gold, exported_name)
        if hasattr(exported, "to_json_schema"):
            schemas.append((exported_name, exported))

    return schemas


def generate_contracts() -> None:
    """Generate JSON Schema contract files for all Gold schemas."""
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    for schema_name, schema_cls in _get_gold_schemas():
        entity_name = _class_name_to_entity(schema_name)
        output_file = CONTRACTS_DIR / f"{entity_name}_{SCHEMA_VERSION}.json"

        print(f"Generating contract for {schema_name} -> {output_file.name}...")
        raw_schema = schema_cls.to_json_schema()
        deterministic_schema = _make_deterministic(raw_schema)
        with output_file.open("w", encoding="utf-8") as file_handle:
            json.dump(
                deterministic_schema,
                file_handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                separators=(",", ": "),
            )
            file_handle.write("\n")

    print(f"Contracts exported to: {CONTRACTS_DIR}")


def main() -> int:
    """CLI entrypoint."""
    try:
        generate_contracts()
    except Exception as error:
        print(f"Failed to export contracts: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

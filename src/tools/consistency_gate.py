"""Consistency gate for canonical registry vs generated schema artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    PROJECT_ROOT / "src" / "bioetl" / "domain" / "schema_registry" / "registry.json"
)
SILVER_PATH = (
    PROJECT_ROOT / "src" / "bioetl" / "infrastructure" / "schemas" / "silver.py"
)
PANDERA_ROOT = PROJECT_ROOT / "src" / "bioetl" / "domain" / "schemas" / "generated"
GOLD_ROOT = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"


def _load_registry() -> dict[str, dict]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {entity["slug"]: entity for entity in payload["entities"]}


def _parse_silver() -> dict[str, list[dict[str, str | bool]]]:
    text = SILVER_PATH.read_text(encoding="utf-8")
    block_pattern = re.compile(
        r"(?ms)^([A-Z0-9_]+)_SCHEMA\s*=\s*pa\.schema\(\s*\[(.*?)\]\s*\)"
    )
    field_pattern = re.compile(
        r'pa\.field\("([^"]+)",\s*(pa\.[a-z0-9_]+\(\))(?:,\s*nullable=(False|True))?\)'
    )
    parsed: dict[str, list[dict[str, str | bool]]] = {}
    for block in block_pattern.finditer(text):
        slug = block.group(1).lower()
        cols = []
        for field in field_pattern.finditer(block.group(2)):
            cols.append(
                {
                    "name": field.group(1),
                    "dtype": field.group(2),
                    "nullable": field.group(3) != "False",
                }
            )
        parsed[slug] = cols
    return parsed


def _parse_pandera(provider: str, entity: str) -> list[dict[str, str | bool]]:
    path = PANDERA_ROOT / provider / f"{entity}.py"
    text = path.read_text(encoding="utf-8")
    dtype_by_annotation = {
        "str": "pa.string()",
        "int": "pa.int64()",
        "float": "pa.float64()",
        "bool": "pa.bool_()",
    }
    full_pattern = re.compile(
        r"^\s*([a-zA-Z0-9_]+):\s+Series\[(str|int|float|bool)\](?:\s+\|\s+None)?\s*=\s*pa\.Field\(nullable=(True|False)\)",
        re.M,
    )
    cols = []
    for match in full_pattern.finditer(text):
        cols.append(
            {
                "name": match.group(1),
                "dtype": dtype_by_annotation[match.group(2)],
                "nullable": match.group(3) == "True",
            }
        )
    return cols


def _parse_gold(slug: str) -> list[dict[str, str | bool]]:
    path = GOLD_ROOT / f"{slug}_v1.0.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cols = []
    for name, spec in payload["properties"].items():
        type_ = spec["type"]
        if isinstance(type_, list):
            base = next(t for t in type_ if t != "null")
        else:
            base = type_
        dtype = {
            "string": "pa.string()",
            "number": "pa.float64()",
            "integer": "pa.int64()",
            "boolean": "pa.bool_()",
        }[base]
        cols.append(
            {
                "name": name,
                "dtype": dtype,
                "nullable": bool(spec.get("nullable", False)),
            }
        )
    return cols


def _normalize_dtype(dtype: str) -> str:
    if dtype == "pa.int64()":
        return "number"
    if dtype == "pa.float64()":
        return "number"
    if dtype == "pa.string()":
        return "string"
    if dtype == "pa.bool_()":
        return "boolean"
    return dtype


def _compare(
    slug: str, expected: list[dict], actual: list[dict], source: str
) -> list[str]:
    errors: list[str] = []
    exp_names = [c["name"] for c in expected]
    act_names = [c["name"] for c in actual]
    if exp_names != act_names:
        errors.append(f"{slug} [{source}]: column order mismatch")
        return errors

    for exp, act in zip(expected, actual, strict=True):
        if _normalize_dtype(exp["dtype"]) != _normalize_dtype(act["dtype"]):
            errors.append(
                f"{slug} [{source}]: dtype mismatch for {exp['name']} expected={exp['dtype']} actual={act['dtype']}"
            )
        if bool(exp["nullable"]) != bool(act["nullable"]):
            errors.append(
                f"{slug} [{source}]: nullable mismatch for {exp['name']} expected={exp['nullable']} actual={act['nullable']}"
            )
    return errors


def main() -> int:
    registry = _load_registry()
    silver = _parse_silver()

    errors: list[str] = []
    for slug, entity in sorted(registry.items()):
        expected = entity["columns"]
        primary_keys = set(entity["primary_keys"])
        for col in expected:
            if col["name"] in primary_keys and col["nullable"]:
                errors.append(f"{slug} [registry]: PK {col['name']} cannot be nullable")

        silver_key = entity.get("schema_constant", "").removesuffix("_SCHEMA").lower()
        errors.extend(_compare(slug, expected, silver.get(silver_key, []), "silver.py"))
        errors.extend(
            _compare(
                slug,
                expected,
                _parse_pandera(entity["provider"], entity["entity"]),
                "pandera",
            )
        )
        errors.extend(_compare(slug, expected, _parse_gold(slug), "gold_contract"))

    if errors:
        print("[FAIL] Consistency gate failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("[OK] Consistency gate passed: PK/nullable/dtype/order are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

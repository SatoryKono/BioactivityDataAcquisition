"""Generate canonical schema registry and derived artifacts.

This script is the single entrypoint for schema artifact generation:
- canonical schema registry JSON
- generated Pandera Silver schemas
- generated PyArrow Silver schemas
- generated Gold JSON contracts
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SILVER_SOURCE = (
    PROJECT_ROOT / "src" / "bioetl" / "infrastructure" / "schemas" / "silver.py"
)
VERIFY_SOURCE = PROJECT_ROOT / "src" / "tools" / "verify_schema_parity.py"
PIPELINES_DIR = PROJECT_ROOT / "configs" / "pipelines"
REGISTRY_PATH = (
    PROJECT_ROOT / "src" / "bioetl" / "domain" / "schema_registry" / "registry.json"
)
PANDERA_OUT = PROJECT_ROOT / "src" / "bioetl" / "domain" / "schemas" / "generated"
SILVER_OUT = (
    PROJECT_ROOT / "src" / "bioetl" / "infrastructure" / "schemas" / "silver.py"
)
GOLD_OUT_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool


@dataclass(frozen=True)
class EntitySpec:
    slug: str
    provider: str
    entity: str
    schema_constant: str
    primary_keys: tuple[str, ...]
    columns: tuple[ColumnSpec, ...]


def _extract_schema_columns() -> dict[str, list[tuple[str, str]]]:
    text = SILVER_SOURCE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(?ms)^([A-Z0-9_]+_SCHEMA)\s*=\s*pa\.schema\(\s*\[(.*?)\]\s*\)"
    )
    field_pattern = re.compile(r'pa\.field\("([^"]+)",\s*(pa\.[a-z0-9_]+\(\))')
    parsed: dict[str, list[tuple[str, str]]] = {}
    for match in pattern.finditer(text):
        const_name = match.group(1)
        body = match.group(2)
        parsed[const_name] = field_pattern.findall(body)
    return parsed


def _extract_config_mapping() -> tuple[dict[str, str], dict[str, str]]:
    text = VERIFY_SOURCE.read_text(encoding="utf-8")
    pair_pattern = re.compile(
        r'SchemaPair\(\s*"([a-z0-9_]+)",\s*([A-Z0-9_]+_SCHEMA),\s*[A-Za-z0-9_]+,\s*"([^"]+)"',
        re.M,
    )
    mapping: dict[str, str] = {}
    const_to_slug: dict[str, str] = {}
    for slug, const_name, config_path in pair_pattern.findall(text):
        mapping[slug] = config_path
        const_to_slug[const_name] = slug
    return mapping, const_to_slug


def _extract_primary_keys(config_path: str) -> tuple[str, ...]:
    path = PROJECT_ROOT / config_path
    if not path.exists():
        return ()
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^primary_keys:\s*\n((?:\s+-\s+[^\n]+\n)+)", text)
    if not match:
        return ()
    keys = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            keys.append(stripped.lstrip("-").strip())
    return tuple(keys)


def _const_to_slug(const_name: str) -> str:
    return const_name.removesuffix("_SCHEMA").lower()


def _slug_to_parts(slug: str) -> tuple[str, str]:
    provider, entity = slug.split("_", 1)
    return provider, entity


def build_registry() -> list[EntitySpec]:
    config_mapping, const_to_slug = _extract_config_mapping()
    raw_schemas = _extract_schema_columns()
    registry: list[EntitySpec] = []
    for const_name in sorted(raw_schemas):
        slug = const_to_slug.get(const_name, _const_to_slug(const_name))
        provider, entity = _slug_to_parts(slug)
        config_path = config_mapping.get(slug, "")
        primary_keys = _extract_primary_keys(config_path) if config_path else ()
        columns: list[ColumnSpec] = []
        for name, dtype in raw_schemas[const_name]:
            nullable = name not in primary_keys
            columns.append(ColumnSpec(name=name, dtype=dtype, nullable=nullable))
        registry.append(
            EntitySpec(
                slug=slug,
                provider=provider,
                entity=entity,
                schema_constant=const_name,
                primary_keys=primary_keys,
                columns=tuple(columns),
            )
        )
    return registry


def write_registry_json(registry: list[EntitySpec]) -> None:
    payload = {
        "generated": True,
        "generated_by": "src/tools/scripts/generate_schema_artifacts.py",
        "entities": [
            {
                "slug": spec.slug,
                "provider": spec.provider,
                "entity": spec.entity,
                "schema_constant": spec.schema_constant,
                "primary_keys": list(spec.primary_keys),
                "columns": [
                    {"name": col.name, "dtype": col.dtype, "nullable": col.nullable}
                    for col in spec.columns
                ],
            }
            for spec in registry
        ],
    }
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _pyarrow_type_to_python(dtype: str) -> str:
    mapping = {
        "pa.string()": "str",
        "pa.int64()": "int",
        "pa.float64()": "float",
        "pa.bool_()": "bool",
    }
    return mapping.get(dtype, "str")


def _class_name(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("_")) + "SilverSchema"


def write_pandera_schemas(registry: list[EntitySpec]) -> None:
    if PANDERA_OUT.exists():
        for file_path in PANDERA_OUT.rglob("*.py"):
            file_path.unlink()
    PANDERA_OUT.mkdir(parents=True, exist_ok=True)
    init_exports: list[str] = []
    init_imports: list[str] = []
    for spec in registry:
        provider_dir = PANDERA_OUT / spec.provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        class_name = _class_name(spec.slug)
        fields_lines: list[str] = []
        for col in spec.columns:
            py_type = _pyarrow_type_to_python(col.dtype)
            annotation = f"Series[{py_type}]"
            if col.nullable:
                annotation = f"{annotation} | None"
            fields_lines.append(
                f"    {col.name}: {annotation} = pa.Field(nullable={col.nullable!s})"
            )
        content = "\n".join(
            [
                '# mypy: ignore-errors',
            '"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""',
                "",
                "# mypy: ignore-errors",
                "from __future__ import annotations",
                "",
                "import pandera.pandas as pa",
                "from pandera.typing import Series",
                "",
                f"class {class_name}(pa.DataFrameModel):",
                '    """Generated Pandera schema from canonical schema registry."""',
                "",
                *fields_lines,
                "",
                "    class Config:",
                "        strict = True",
                "        ordered = True",
                "        coerce = True",
                "",
            ]
        )
        module_path = provider_dir / f"{spec.entity}.py"
        module_path.write_text(content, encoding="utf-8")

        provider_init = provider_dir / "__init__.py"
        if not provider_init.exists():
            provider_init.write_text(
                '"""AUTO-GENERATED PACKAGE."""\n', encoding="utf-8"
            )

        init_imports.append(
            f"from bioetl.domain.schemas.generated.{spec.provider}.{spec.entity} import {class_name}"
        )
        init_exports.append(f'    "{class_name}",')

    init_content = "\n".join(
        [
            '"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""',
            "",
            *sorted(init_imports),
            "",
            "__all__ = [",
            *sorted(init_exports),
            "]",
            "",
        ]
    )
    (PANDERA_OUT / "__init__.py").write_text(init_content, encoding="utf-8")


def write_silver_py(registry: list[EntitySpec]) -> None:
    lines = [
        '"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""',
        "",
        "from __future__ import annotations",
        "",
        "import pyarrow as pa",
        "",
    ]
    for spec in registry:
        lines.append(f"{spec.schema_constant} = pa.schema(")
        lines.append("    [")
        for col in spec.columns:
            if col.nullable:
                lines.append(f'        pa.field("{col.name}", {col.dtype}),')
            else:
                lines.append(
                    f'        pa.field("{col.name}", {col.dtype}, nullable=False),'
                )
        lines.append("    ]")
        lines.append(")")
        lines.append("")
    SILVER_OUT.write_text("\n".join(lines), encoding="utf-8")


def _json_type_for(col: ColumnSpec) -> str | list[str]:
    if col.dtype == "pa.string()":
        base = "string"
    elif col.dtype in {"pa.int64()", "pa.float64()"}:
        base = "number"
    elif col.dtype == "pa.bool_()":
        base = "boolean"
    else:
        base = "string"
    return [base, "null"] if col.nullable else base


def write_gold_contracts(registry: list[EntitySpec]) -> None:
    GOLD_OUT_DIR.mkdir(parents=True, exist_ok=True)
    provider_prefixes = {f"{spec.provider}_" for spec in registry}
    for path in GOLD_OUT_DIR.glob("*_v1.0.json"):
        if any(path.name.startswith(prefix) for prefix in provider_prefixes):
            path.unlink()
    for spec in registry:
        properties = {
            col.name: {
                "type": _json_type_for(col),
                "nullable": col.nullable,
                "description": "",
            }
            for col in spec.columns
        }
        required = [col.name for col in spec.columns if not col.nullable]
        payload = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$version": "1.0.0",
            "title": f"{_class_name(spec.slug)} Contract",
            "description": (
                f"AUTO-GENERATED from canonical schema registry for {spec.slug}."
            ),
            "type": "object",
            "properties": properties,
            "required": required,
        }
        path = GOLD_OUT_DIR / f"{spec.slug}_v1.0.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def main() -> None:
    registry = build_registry()
    write_registry_json(registry)
    write_pandera_schemas(registry)
    write_silver_py(registry)
    write_gold_contracts(registry)
    print(f"Generated schema artifacts for {len(registry)} entities.")


if __name__ == "__main__":
    main()

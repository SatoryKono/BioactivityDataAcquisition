#!/usr/bin/env python3
"""Generate a unified Bronze→Silver→Gold schema map for all entity pipelines.

The map combines three canonical sources without importing the runtime package:
  - ``configs/entities/*.yaml`` for Bronze→Silver→Gold selection policy
  - pipeline registry manifests for Silver PyArrow / Silver Pandera / Gold wiring
  - source AST for Silver and Gold schema field extraction

Output is a UTF-8 CSV intended for audit, documentation, and cross-layer comparison.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlunsplit

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"
SRC_DIR = PROJECT_ROOT / "src"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "unified_schema_map.csv"
JSON_SCHEMA_DRAFT7_URI = urlunsplit(("http", "json-schema.org", "/draft-07/schema", "", ""))

CHEMBL_MANIFEST = (
    SRC_DIR
    / "bioetl"
    / "composition"
    / "factories"
    / "pipeline"
    / "_registry_manifest_chembl.py"
)
NON_CHEMBL_MANIFEST = (
    SRC_DIR
    / "bioetl"
    / "composition"
    / "factories"
    / "pipeline"
    / "_registry_manifest_non_chembl.py"
)

SILVER_SCHEMA_DIR = SRC_DIR / "bioetl" / "infrastructure" / "schemas"
DOMAIN_SCHEMA_DIR = SRC_DIR / "bioetl" / "domain" / "schemas"
GOLD_CONTRACT_DIR = SRC_DIR / "bioetl" / "domain" / "contracts" / "gold"
PUBLICATION_FIELD_BLOCKS = SILVER_SCHEMA_DIR / "silver_publication_field_blocks.py"

CSV_COLUMNS: tuple[str, ...] = (
    "provider",
    "entity",
    "pipeline_name",
    "config_path",
    "silver_pyarrow_schema",
    "silver_pyarrow_fields_json",
    "silver_pandera_model",
    "silver_pandera_fields_json",
    "gold_contract_class",
    "gold_json_contract",
    "bronze_column_groups_json",
    "silver_include_groups_json",
    "silver_exclude_fields_json",
    "gold_include_groups_json",
    "gold_exclude_fields_json",
    "silver_pyarrow_columns_json",
    "silver_pandera_columns_json",
    "gold_columns_json",
    "layer_flow_summary_json",
)


@dataclass(frozen=True)
class PipelineBinding:
    """Static pipeline binding extracted from registry manifests."""

    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema_symbol: str
    gold_schema_symbol: str
    pandera_silver_symbol: str


@dataclass(frozen=True)
class SymbolLocation:
    """Resolved source location for a static symbol."""

    module: str
    path: Path

    @property
    def qualified_prefix(self) -> str:
        return self.module


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _entity_config_paths() -> list[Path]:
    return sorted(path for path in ENTITIES_DIR.rglob("*.yaml") if path.is_file())


def _read_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _literal_string(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _literal_bool(node: ast.AST | None, *, default: bool) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return default


def _list_of_strings(node: ast.AST | None) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return []
    values: list[str] = []
    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.append(item.value)
    return values


def _module_name_from_path(path: Path) -> str:
    relative = path.relative_to(SRC_DIR)
    return ".".join(relative.with_suffix("").parts)


def _kw_value(call: ast.Call, keyword: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return None


def _field_json_type(type_hint: str) -> str:
    normalized = type_hint.lower()
    if "series[str" in normalized or normalized in {"str", "string"}:
        return "string"
    if (
        "series[int" in normalized
        or "int64dtype" in normalized
        or normalized.startswith("int")
    ):
        return "integer"
    if "series[float" in normalized or normalized.startswith("float"):
        return "number"
    if "series[bool" in normalized or normalized == "bool":
        return "boolean"
    return "object"


def _normalized_gold_export_name(column_name: str) -> str:
    if column_name.endswith("_chembl_id"):
        return column_name.replace("_chembl_id", "_id")
    return column_name


def _assigned_value(node: ast.stmt) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _binding_from_pipeline_call(element: ast.Call) -> PipelineBinding | None:
    if not isinstance(element.func, ast.Name) or element.func.id != "PipelineFactoryConfig":
        return None

    kwargs = {kw.arg: kw.value for kw in element.keywords if kw.arg is not None}
    pipeline_name = _literal_string(kwargs.get("pipeline_name"))
    if not pipeline_name:
        return None

    def _symbol_name(keyword: str) -> str:
        value = kwargs.get(keyword)
        return value.id if isinstance(value, ast.Name) else ""

    return PipelineBinding(
        pipeline_name=pipeline_name,
        provider=_literal_string(kwargs.get("provider")),
        entity_type=_literal_string(kwargs.get("entity_type")),
        silver_schema_symbol=_symbol_name("silver_schema"),
        gold_schema_symbol=_symbol_name("gold_schema"),
        pandera_silver_symbol=_symbol_name("pandera_silver_schema"),
    )


def _extract_manifest_bindings(path: Path) -> list[PipelineBinding]:
    tree = _read_ast(path)
    bindings: list[PipelineBinding] = []

    for node in tree.body:
        value = _assigned_value(node)
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue

        for element in value.elts:
            if not isinstance(element, ast.Call):
                continue
            binding = _binding_from_pipeline_call(element)
            if binding is not None:
                bindings.append(binding)

    return bindings


def _pipeline_registry() -> dict[str, PipelineBinding]:
    registry: dict[str, PipelineBinding] = {}
    for manifest in (CHEMBL_MANIFEST, NON_CHEMBL_MANIFEST):
        for binding in _extract_manifest_bindings(manifest):
            registry[binding.pipeline_name] = binding
    return registry


def _scan_pyarrow_schemas() -> dict[str, SymbolLocation]:
    registry: dict[str, SymbolLocation] = {}
    for path in SILVER_SCHEMA_DIR.glob("*.py"):
        tree = _read_ast(path)
        module = _module_name_from_path(path)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            symbol = node.targets[0].id
            if not symbol.endswith("_SCHEMA"):
                continue
            registry[symbol] = SymbolLocation(module=module, path=path)
    return registry


def _scan_pandera_models(
    root: Path, *, suffix: str = "Schema"
) -> dict[str, SymbolLocation]:
    registry: dict[str, SymbolLocation] = {}
    for path in root.rglob("*.py"):
        tree = _read_ast(path)
        module = _module_name_from_path(path)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith(suffix):
                continue
            registry[node.name] = SymbolLocation(module=module, path=path)
    return registry


def _parse_pyarrow_field_call(field_call: ast.Call) -> dict[str, object] | None:
    func = field_call.func
    if not isinstance(func, ast.Attribute) or func.attr != "field":
        return None
    name = _literal_string(field_call.args[0] if field_call.args else None)
    dtype = ast.unparse(field_call.args[1]) if len(field_call.args) > 1 else "object"
    nullable = _literal_bool(_kw_value(field_call, "nullable"), default=True)
    if not name:
        return None
    return {"name": name, "type": dtype, "nullable": nullable}


def _scan_pyarrow_field_blocks(path: Path) -> dict[str, list[dict[str, object]]]:
    tree = _read_ast(path)
    blocks: dict[str, list[dict[str, object]]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Return):
                continue
            if not isinstance(statement.value, ast.List):
                continue
            fields: list[dict[str, object]] = []
            for element in statement.value.elts:
                if not isinstance(element, ast.Call):
                    continue
                parsed = _parse_pyarrow_field_call(element)
                if parsed is not None:
                    fields.append(parsed)
            if fields:
                blocks[node.name] = fields
    return blocks


def _expand_pyarrow_fields(
    node: ast.AST | None,
    *,
    field_blocks: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    if isinstance(node, ast.List):
        fields: list[dict[str, object]] = []
        for element in node.elts:
            if isinstance(element, ast.Call):
                parsed = _parse_pyarrow_field_call(element)
                if parsed is not None:
                    fields.append(parsed)
                    continue
                if isinstance(element.func, ast.Name):
                    fields.extend(field_blocks.get(element.func.id, []))
                    continue
            if isinstance(element, ast.Starred) and isinstance(element.value, ast.Call):
                if isinstance(element.value.func, ast.Name):
                    fields.extend(field_blocks.get(element.value.func.id, []))
        return fields

    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "schema":
            return _expand_pyarrow_fields(
                node.args[0] if node.args else None,
                field_blocks=field_blocks,
            )
        if isinstance(func, ast.Name) and func.id == "_build_publication_schema":
            provider_fields = _expand_pyarrow_fields(
                node.args[0] if node.args else None,
                field_blocks=field_blocks,
            )
            return (
                field_blocks.get("build_publication_system_prefix_fields", [])
                + provider_fields
                + field_blocks.get("build_publication_dq_suffix_fields", [])
            )
        if isinstance(func, ast.Name):
            return field_blocks.get(func.id, [])

    return []


def _extract_pyarrow_fields(
    path: Path,
    symbol: str,
    *,
    field_blocks: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    tree = _read_ast(path)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != symbol:
            continue
        return _expand_pyarrow_fields(node.value, field_blocks=field_blocks)
    return []


def _find_class_node(path: Path, class_name: str) -> ast.ClassDef | None:
    tree = _read_ast(path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _base_class_names(node: ast.ClassDef) -> list[str]:
    base_names: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_names.append(base.id)
        elif isinstance(base, ast.Attribute):
            base_names.append(base.attr)
    return base_names


def _merge_base_pandera_fields(
    *,
    node: ast.ClassDef,
    model_locations: dict[str, SymbolLocation],
    visited: set[tuple[Path, str]],
) -> dict[str, dict[str, object]]:
    field_map: dict[str, dict[str, object]] = {}
    for base_name in _base_class_names(node):
        base_location = model_locations.get(base_name)
        if base_location is None:
            continue
        for field in _extract_pandera_fields(
            base_location.path,
            base_name,
            model_locations=model_locations,
            seen=visited,
        ):
            field_map[str(field["name"])] = field
    return field_map


def _extract_annassign_field(class_item: ast.stmt) -> dict[str, object] | None:
    if not isinstance(class_item, ast.AnnAssign):
        return None
    if not isinstance(class_item.target, ast.Name):
        return None
    if not isinstance(class_item.value, ast.Call):
        return None
    func = class_item.value.func
    if not isinstance(func, ast.Attribute) or func.attr != "Field":
        return None

    target_name = class_item.target.id
    alias = _literal_string(_kw_value(class_item.value, "alias"))
    exported_name = alias or target_name
    type_hint = ast.unparse(class_item.annotation)
    nullable = _literal_bool(_kw_value(class_item.value, "nullable"), default=False)
    description = _literal_string(_kw_value(class_item.value, "description"))
    return {
        "name": exported_name,
        "source_name": target_name,
        "dtype": type_hint,
        "nullable": nullable,
        "required": not nullable,
        "description": description,
    }


def _extract_pandera_fields(
    path: Path,
    class_name: str,
    *,
    model_locations: dict[str, SymbolLocation],
    seen: set[tuple[Path, str]] | None = None,
) -> list[dict[str, object]]:
    visit_key = (path, class_name)
    visited = seen if seen is not None else set()
    if visit_key in visited:
        return []
    visited.add(visit_key)

    node = _find_class_node(path, class_name)
    if node is None:
        return []

    field_map = _merge_base_pandera_fields(
        node=node,
        model_locations=model_locations,
        visited=visited,
    )
    for class_item in node.body:
        extracted = _extract_annassign_field(class_item)
        if extracted is not None:
            field_map[str(extracted["name"])] = extracted

    return list(field_map.values())


def _resolve_required_location(
    *,
    locations: dict[str, SymbolLocation],
    symbol: str,
    label: str,
) -> SymbolLocation:
    location = locations.get(symbol)
    if location is None:
        raise ValueError(f"No {label} source found for {symbol}")
    return location


def _column_names(fields: list[dict[str, object]], *, key: str = "name") -> list[object]:
    return [field[key] for field in fields]


def _build_layer_flow_summary(
    *,
    bronze_groups: list[dict[str, object]],
    silver_pyarrow_ref: str,
    silver_include_groups: list[str],
    silver_exclude_fields: list[str],
    silver_pyarrow_columns: list[object],
    silver_pandera_columns: list[object],
    gold_contract_ref: str,
    gold_include_groups: list[str],
    gold_exclude_fields: list[str],
    gold_columns: list[object],
) -> dict[str, object]:
    return {
        "bronze": {"column_groups": bronze_groups},
        "silver": {
            "pyarrow_schema": silver_pyarrow_ref,
            "include_groups": silver_include_groups,
            "exclude_fields": silver_exclude_fields,
            "columns": silver_pyarrow_columns,
            "pandera_columns": silver_pandera_columns,
        },
        "gold": {
            "contract_class": gold_contract_ref,
            "include_groups": gold_include_groups,
            "exclude_fields": gold_exclude_fields,
            "columns": gold_columns,
        },
    }


def _build_gold_json_contract(path: Path, class_name: str) -> dict[str, object]:
    fields = _extract_pandera_fields(
        path,
        class_name,
        model_locations=_scan_pandera_models(GOLD_CONTRACT_DIR, suffix="Schema"),
    )
    properties: dict[str, dict[str, object]] = {}
    required: list[str] = []

    for field in fields:
        export_name = _normalized_gold_export_name(str(field["name"]))
        nullable = bool(field["nullable"])
        base_type = _field_json_type(str(field["dtype"]))
        json_type: str | list[str] = [base_type, "null"] if nullable else base_type
        properties[export_name] = {
            "type": json_type,
            "nullable": nullable,
            "description": field["description"],
        }
        if not nullable:
            required.append(export_name)

    return {
        "$schema": f"{JSON_SCHEMA_DRAFT7_URI}#",
        "title": f"{class_name} Contract",
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def _extract_column_groups(config: dict[str, Any]) -> list[dict[str, object]]:
    schema_section = config.get("schema")
    if not isinstance(schema_section, dict):
        return []

    column_groups = schema_section.get("column_groups")
    if not isinstance(column_groups, list):
        return []

    groups: list[dict[str, object]] = []
    for raw_group in column_groups:
        if not isinstance(raw_group, dict):
            continue
        name = raw_group.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        fields = raw_group.get("fields")
        pattern = raw_group.get("pattern")
        groups.append(
            {
                "name": name,
                "fields": list(fields) if isinstance(fields, list) else [],
                "pattern": pattern if isinstance(pattern, str) else "",
            }
        )
    return groups


def _schema_policy(config: dict[str, Any], layer: str) -> tuple[list[str], list[str]]:
    schema_section = config.get("schema")
    if not isinstance(schema_section, dict):
        return [], []

    layer_section = schema_section.get(layer)
    if not isinstance(layer_section, dict):
        return [], []

    include_groups = layer_section.get("include_groups")
    exclude_fields = layer_section.get("exclude_fields")
    return (
        list(include_groups) if isinstance(include_groups, list) else [],
        list(exclude_fields) if isinstance(exclude_fields, list) else [],
    )


def _pipeline_name(config: dict[str, Any], *, path: Path) -> str:
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        raise ValueError(f"{path.relative_to(PROJECT_ROOT)}: missing pipeline section")

    pipeline_name = pipeline.get("pipeline_name")
    if not isinstance(pipeline_name, str) or not pipeline_name.strip():
        raise ValueError(
            f"{path.relative_to(PROJECT_ROOT)}: missing pipeline.pipeline_name"
        )
    return pipeline_name


def _resolved_layer_locations(
    *,
    binding: PipelineBinding,
    pyarrow_locations: dict[str, SymbolLocation],
    pandera_locations: dict[str, SymbolLocation],
    gold_locations: dict[str, SymbolLocation],
) -> tuple[SymbolLocation, SymbolLocation, SymbolLocation]:
    return (
        _resolve_required_location(
            locations=pyarrow_locations,
            symbol=binding.silver_schema_symbol,
            label="PyArrow schema",
        ),
        _resolve_required_location(
            locations=pandera_locations,
            symbol=binding.pandera_silver_symbol,
            label="Pandera",
        ),
        _resolve_required_location(
            locations=gold_locations,
            symbol=binding.gold_schema_symbol,
            label="Gold contract",
        ),
    )


def _schema_refs(
    *,
    binding: PipelineBinding,
    pyarrow_location: SymbolLocation,
    pandera_location: SymbolLocation,
    gold_location: SymbolLocation,
) -> tuple[str, str, str]:
    return (
        f"{pyarrow_location.qualified_prefix}.{binding.silver_schema_symbol}",
        f"{pandera_location.qualified_prefix}.{binding.pandera_silver_symbol}",
        f"{gold_location.qualified_prefix}.{binding.gold_schema_symbol}",
    )


def _layer_schema_payloads(
    *,
    binding: PipelineBinding,
    pyarrow_location: SymbolLocation,
    pandera_location: SymbolLocation,
    gold_location: SymbolLocation,
    pandera_locations: dict[str, SymbolLocation],
    pyarrow_field_blocks: dict[str, list[dict[str, object]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    pyarrow_fields = _extract_pyarrow_fields(
        pyarrow_location.path,
        binding.silver_schema_symbol,
        field_blocks=pyarrow_field_blocks,
    )
    pandera_fields = _extract_pandera_fields(
        pandera_location.path,
        binding.pandera_silver_symbol,
        model_locations=pandera_locations,
    )
    gold_json_contract = _build_gold_json_contract(
        gold_location.path,
        binding.gold_schema_symbol,
    )
    return pyarrow_fields, pandera_fields, gold_json_contract


def _config_schema_policy_payload(
    config: dict[str, Any],
) -> tuple[list[dict[str, object]], list[str], list[str], list[str], list[str]]:
    bronze_groups = _extract_column_groups(config)
    silver_include_groups, silver_exclude_fields = _schema_policy(config, "silver")
    gold_include_groups, gold_exclude_fields = _schema_policy(config, "gold")
    return (
        bronze_groups,
        silver_include_groups,
        silver_exclude_fields,
        gold_include_groups,
        gold_exclude_fields,
    )


def _build_row(
    path: Path,
    *,
    config: dict[str, Any],
    binding: PipelineBinding,
    pyarrow_locations: dict[str, SymbolLocation],
    pandera_locations: dict[str, SymbolLocation],
    gold_locations: dict[str, SymbolLocation],
    pyarrow_field_blocks: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    provider = str(config.get("provider", binding.provider))
    entity = str(config.get("entity", binding.entity_type))
    pipeline_name = _pipeline_name(config, path=path)

    pyarrow_location, pandera_location, gold_location = _resolved_layer_locations(
        binding=binding,
        pyarrow_locations=pyarrow_locations,
        pandera_locations=pandera_locations,
        gold_locations=gold_locations,
    )

    pyarrow_fields, pandera_fields, gold_json_contract = _layer_schema_payloads(
        binding=binding,
        pyarrow_location=pyarrow_location,
        pandera_location=pandera_location,
        gold_location=gold_location,
        pandera_locations=pandera_locations,
        pyarrow_field_blocks=pyarrow_field_blocks,
    )

    (
        bronze_groups,
        silver_include_groups,
        silver_exclude_fields,
        gold_include_groups,
        gold_exclude_fields,
    ) = _config_schema_policy_payload(config)

    silver_pyarrow_columns = _column_names(pyarrow_fields)
    silver_pandera_columns = _column_names(pandera_fields)
    gold_columns = list(
        cast("dict[str, object]", gold_json_contract["properties"]).keys()
    )

    silver_pyarrow_ref, silver_pandera_ref, gold_contract_ref = _schema_refs(
        binding=binding,
        pyarrow_location=pyarrow_location,
        pandera_location=pandera_location,
        gold_location=gold_location,
    )

    layer_flow = _build_layer_flow_summary(
        bronze_groups=bronze_groups,
        silver_pyarrow_ref=silver_pyarrow_ref,
        silver_include_groups=silver_include_groups,
        silver_exclude_fields=silver_exclude_fields,
        silver_pyarrow_columns=silver_pyarrow_columns,
        silver_pandera_columns=silver_pandera_columns,
        gold_contract_ref=gold_contract_ref,
        gold_include_groups=gold_include_groups,
        gold_exclude_fields=gold_exclude_fields,
        gold_columns=gold_columns,
    )

    return {
        "provider": provider,
        "entity": entity,
        "pipeline_name": pipeline_name,
        "config_path": path.relative_to(PROJECT_ROOT).as_posix(),
        "silver_pyarrow_schema": silver_pyarrow_ref,
        "silver_pyarrow_fields_json": _json_dump(pyarrow_fields),
        "silver_pandera_model": silver_pandera_ref,
        "silver_pandera_fields_json": _json_dump(pandera_fields),
        "gold_contract_class": gold_contract_ref,
        "gold_json_contract": _json_dump(gold_json_contract),
        "bronze_column_groups_json": _json_dump(bronze_groups),
        "silver_include_groups_json": _json_dump(silver_include_groups),
        "silver_exclude_fields_json": _json_dump(silver_exclude_fields),
        "gold_include_groups_json": _json_dump(gold_include_groups),
        "gold_exclude_fields_json": _json_dump(gold_exclude_fields),
        "silver_pyarrow_columns_json": _json_dump(silver_pyarrow_columns),
        "silver_pandera_columns_json": _json_dump(silver_pandera_columns),
        "gold_columns_json": _json_dump(gold_columns),
        "layer_flow_summary_json": _json_dump(layer_flow),
    }


def _build_row_from_config_path(
    path: Path,
    *,
    registry: dict[str, PipelineBinding],
    pyarrow_locations: dict[str, SymbolLocation],
    pandera_locations: dict[str, SymbolLocation],
    gold_locations: dict[str, SymbolLocation],
    pyarrow_field_blocks: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    config = _load_yaml(path)
    pipeline_name = _pipeline_name(config, path=path)
    binding = registry.get(pipeline_name)
    if binding is None:
        raise ValueError(
            f"No pipeline registry entry found for {pipeline_name} "
            f"({path.relative_to(PROJECT_ROOT).as_posix()})"
        )
    return _build_row(
        path,
        config=config,
        binding=binding,
        pyarrow_locations=pyarrow_locations,
        pandera_locations=pandera_locations,
        gold_locations=gold_locations,
        pyarrow_field_blocks=pyarrow_field_blocks,
    )


def build_unified_schema_rows() -> list[dict[str, str]]:
    registry = _pipeline_registry()
    pyarrow_locations = _scan_pyarrow_schemas()
    pandera_locations = _scan_pandera_models(DOMAIN_SCHEMA_DIR)
    gold_locations = _scan_pandera_models(GOLD_CONTRACT_DIR, suffix="Schema")
    pyarrow_field_blocks = _scan_pyarrow_field_blocks(PUBLICATION_FIELD_BLOCKS)
    rows: list[dict[str, str]] = []

    for path in _entity_config_paths():
        rows.append(
            _build_row_from_config_path(
                path,
                registry=registry,
                pyarrow_locations=pyarrow_locations,
                pandera_locations=pandera_locations,
                gold_locations=gold_locations,
                pyarrow_field_blocks=pyarrow_field_blocks,
            )
        )

    rows.sort(key=lambda row: (row["provider"], row["entity"], row["pipeline_name"]))
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a unified Bronze→Silver→Gold schema map as UTF-8 CSV."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    rows = build_unified_schema_rows()
    write_csv(rows, output_path)
    print(
        f"Generated {output_path.relative_to(PROJECT_ROOT)} with {len(rows)} entity mappings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

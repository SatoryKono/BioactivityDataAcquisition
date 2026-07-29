#!/usr/bin/env python3
"""Build a deterministic, typed dataflow IR for one entity pipeline."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Protocol, cast

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from scripts.schema.generate_unified_schema_map import build_unified_schema_row

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IR_SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"

_SYSTEM_PREFIX = (
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_source",
    "_ingestion_ts",
    "_index",
)
_DQ_SUFFIX = ("_dq_error", "_dq_warn")
type _JsonObject = dict[str, Any]


def _source_date() -> str:
    """Return the last canonical input change date without wall-clock entropy."""
    result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--format=%cs",
            "--",
            "configs",
            "src/bioetl",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class _ArrowField(Protocol):
    type: object
    nullable: bool


class _ArrowSchema(Protocol):
    names: list[str]

    def field(self, name: str) -> _ArrowField: ...


@dataclass(frozen=True, slots=True)
class SourceRefIR:
    """One canonical input used to resolve the generated pipeline view."""

    kind: str
    path: str
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class CriterionIR:
    """A source query or record-level filtering criterion."""

    stage: str
    category: str
    field: str
    operator: str
    value: object
    source_key: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class FieldIR:
    """An output field published by one medallion layer."""

    ordinal: int
    name: str
    data_type: str
    nullable: bool
    required: bool
    group: str
    schema_source: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class LayerIR:
    """Resolved layer projection and its governing schema policy."""

    name: str
    schema_ref: str
    include_groups: tuple[str, ...]
    exclude_fields: tuple[str, ...]
    contract_field_count: int
    fields: tuple[FieldIR, ...]
    omitted_contract_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PostProcessingIR:
    """Declarative and code-defined post-processing surfaces."""

    transformer_class: str
    declarative_steps: tuple[object, ...]
    code_defined_methods: tuple[str, ...]
    inspection_policy: str


@dataclass(frozen=True, slots=True)
class DQSummaryIR:
    """Effective DQ policy and rule inventory."""

    soft_fail_threshold: float
    hard_fail_threshold: float
    strict_validation: bool
    invalid_record_policy: str
    field_validations: tuple[dict[str, object], ...]
    cross_field_validations: tuple[dict[str, object], ...]
    conditional_validations: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class DiagnosticIR:
    """A non-fatal mismatch made explicit in generated documentation."""

    code: str
    severity: str
    message: str
    fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PipelineDataflowIR:
    """Complete source-backed representation used by every generated view."""

    schema_version: str
    generator_version: str
    generated_date: str
    pipeline_name: str
    provider: str
    entity: str
    effective_config_sha256: str
    effective_config_loader: str
    source_profile: dict[str, object]
    sources: tuple[SourceRefIR, ...]
    extraction_criteria: tuple[CriterionIR, ...]
    input_criteria: tuple[CriterionIR, ...]
    silver_criteria: tuple[CriterionIR, ...]
    gold_criteria: tuple[CriterionIR, ...]
    silver: LayerIR
    gold: LayerIR
    post_processing: PostProcessingIR
    dq: DQSummaryIR
    diagnostics: tuple[DiagnosticIR, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation with deterministic values."""
        return cast(dict[str, object], _json_compatible(asdict(self)))


def _json_compatible(value: Any) -> Any:  # Any: recursive JSON normalization
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _import_arrow_schema(qualified_name: str) -> _ArrowSchema:
    module_name, symbol_name = qualified_name.rsplit(".", 1)
    return cast(
        _ArrowSchema, getattr(importlib.import_module(module_name), symbol_name)
    )


def _module_path(qualified_name: str) -> str:
    module_name = qualified_name.rsplit(".", 1)[0]
    return f"src/{module_name.replace('.', '/')}.py"


def _group_for(field: str, groups: list[_JsonObject]) -> str:
    for group in groups:
        fields = group.get("fields") or []
        if field in fields:
            return str(group["name"])
        pattern = group.get("pattern")
        if pattern and re.search(str(pattern), field):
            return str(group["name"])
    return "unmapped"


def _append_projected_group(
    group: _JsonObject,
    *,
    available: set[str],
    selected: list[str],
    used: set[str],
) -> None:
    """Append one configured group's explicit and pattern-matched fields."""
    for field in group.get("fields") or []:
        name = str(field)
        if name in available and name not in used:
            selected.append(name)
            used.add(name)

    pattern = group.get("pattern")
    if not pattern:
        return
    for name in sorted(available - used):
        if re.search(str(pattern), name):
            selected.append(name)
            used.add(name)


def _project_fields(
    available: list[str],
    *,
    groups: list[_JsonObject],
    include_groups: list[str],
    exclude_fields: list[str],
) -> list[str]:
    """Mirror runtime group projection for non-qualified entity fields."""
    available_set = set(available)
    selected: list[str] = []
    used: set[str] = set()
    by_name = {str(group["name"]): group for group in groups}
    missing = [group_name for group_name in include_groups if group_name not in by_name]
    if missing:
        raise ValueError(
            f"Unknown column groups: {missing}; available: {sorted(by_name)}"
        )

    # Match runtime: preserve column_groups YAML order, not include_groups order.
    include_set = set(include_groups)
    ordered_include = [
        str(group["name"]) for group in groups if str(group["name"]) in include_set
    ]
    for group_name in ordered_include:
        _append_projected_group(
            by_name[group_name],
            available=available_set,
            selected=selected,
            used=used,
        )

    selected = [
        name
        for name in selected
        if not any(fnmatch(name, pattern) for pattern in exclude_fields)
    ]
    prefix = [name for name in _SYSTEM_PREFIX if name in selected]
    suffix = [name for name in _DQ_SUFFIX if name in selected]
    fixed = {*prefix, *suffix}
    return [*prefix, *(name for name in selected if name not in fixed), *suffix]


def _extraction_criteria(params: dict[str, object]) -> tuple[CriterionIR, ...]:
    criteria: list[CriterionIR] = []
    for source_key, value in params.items():
        if source_key.endswith("__in"):
            field, operator = source_key.removesuffix("__in"), "in"
        elif source_key.endswith("__isnull"):
            field = source_key.removesuffix("__isnull")
            operator = "is null" if value is True else "is not null"
        else:
            field, operator = source_key, "="
        criteria.append(
            CriterionIR(
                stage="source",
                category="api query",
                field=field,
                operator=operator,
                value=value,
                source_key=source_key,
            )
        )
    return tuple(criteria)


def _layer_criteria(stage: str, config: dict[str, Any]) -> tuple[CriterionIR, ...]:
    criteria: list[CriterionIR] = []
    for field, value in (config.get("columns") or {}).items():
        criteria.append(
            CriterionIR(stage, "column", str(field), "in", value, f"columns.{field}")
        )
    for field, value in (config.get("ranges") or {}).items():
        criteria.append(
            CriterionIR(stage, "range", str(field), "range", value, f"ranges.{field}")
        )
    for field, value in (config.get("list_lengths") or {}).items():
        criteria.append(
            CriterionIR(
                stage,
                "list length",
                str(field),
                "length",
                value,
                f"list_lengths.{field}",
            )
        )
    for field, value in (config.get("list_contains") or {}).items():
        criteria.append(
            CriterionIR(
                stage,
                "list content",
                str(field),
                "contains",
                value,
                f"list_contains.{field}",
            )
        )
    for field in config.get("required_fields") or []:
        criteria.append(
            CriterionIR(
                stage,
                "structural",
                str(field),
                "is not null",
                True,
                f"required_fields.{field}",
            )
        )
    for field in config.get("exclude_if_present") or []:
        criteria.append(
            CriterionIR(
                stage,
                "structural",
                str(field),
                "exclude if present",
                True,
                f"exclude_if_present.{field}",
            )
        )
    return tuple(criteria)


def _code_defined_methods(transformer_class: str) -> tuple[str, ...]:
    source_path = PROJECT_ROOT / _module_path(transformer_class)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    class_name = transformer_class.rsplit(".", 1)[-1]
    interesting = {"_postprocess_pre_silver_record", "transform_for_gold"}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return tuple(
                child.name
                for child in node.body
                if isinstance(child, ast.FunctionDef) and child.name in interesting
            )
    return ()


def _build_dq(configs_root: Path, provider: str, entity: str) -> DQSummaryIR:
    payload = _json_compatible(
        asdict(DQConfigLoader(configs_root).load(provider, entity))
    )
    return DQSummaryIR(
        soft_fail_threshold=float(payload["soft_fail_threshold"]),
        hard_fail_threshold=float(payload["hard_fail_threshold"]),
        strict_validation=bool(payload["strict_validation"]),
        invalid_record_policy=str(payload["invalid_record_policy"]),
        field_validations=tuple(payload["field_validations"]),
        cross_field_validations=tuple(payload["cross_field_validations"]),
        conditional_validations=tuple(payload["conditional_validations"]),
    )


def _build_sources(
    *,
    provider: str,
    entity: str,
    schema_row: dict[str, str],
    transformer_class: str,
) -> tuple[SourceRefIR, ...]:
    config_paths = (
        "configs/base/pipeline.yaml",
        "configs/base/quality.yaml",
        f"configs/providers/{provider}.yaml",
        f"configs/entities/{provider}/{entity}.yaml",
    )
    refs = [
        SourceRefIR("effective config layer", path)
        for path in config_paths
        if (PROJECT_ROOT / path).is_file()
    ]
    refs.extend(
        (
            SourceRefIR(
                "pipeline registry",
                "src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py",
                f"{provider}_{entity}",
            ),
            SourceRefIR(
                "Silver PyArrow schema",
                _module_path(schema_row["silver_pyarrow_schema"]),
                schema_row["silver_pyarrow_schema"],
            ),
            SourceRefIR(
                "Silver Pandera schema",
                _module_path(schema_row["silver_pandera_model"]),
                schema_row["silver_pandera_model"],
            ),
            SourceRefIR(
                "Gold contract",
                _module_path(schema_row["gold_contract_class"]),
                schema_row["gold_contract_class"],
            ),
            SourceRefIR(
                "transformer",
                _module_path(transformer_class),
                transformer_class,
            ),
        )
    )
    return tuple(refs)


def build_pipeline_dataflow_ir(
    pipeline_name: str,
    *,
    configs_root: Path | None = None,
) -> PipelineDataflowIR:
    """Resolve live config and contracts into the canonical pipeline diagram IR."""
    root = (configs_root or PROJECT_ROOT / "configs").resolve()
    config = load_pipeline_config_from_root(pipeline_name, configs_root=root)
    effective = cast(_JsonObject, _json_compatible(config.model_dump(mode="json")))
    provider = str(effective["provider"])
    entity = str(effective["entity_type"])
    schema_row = build_unified_schema_row(pipeline_name, configs_root=root)

    groups = cast(list[_JsonObject], effective["data_schema"]["column_groups"])
    silver_policy = cast(_JsonObject, effective["data_schema"]["silver"])
    gold_policy = cast(_JsonObject, effective["data_schema"]["gold"])

    silver_schema = _import_arrow_schema(schema_row["silver_pyarrow_schema"])
    silver_metadata = {
        item["name"]: item
        for item in json.loads(schema_row["silver_pandera_fields_json"])
    }
    silver_names = list(silver_schema.names)
    silver_output = _project_fields(
        silver_names,
        groups=groups,
        include_groups=list(silver_policy["include_groups"]),
        exclude_fields=list(silver_policy["exclude_fields"]),
    )
    if set(silver_output) != set(silver_names):
        missing = sorted(set(silver_names) - set(silver_output))
        raise ValueError(f"Silver projection omits schema fields: {missing}")
    silver_fields = tuple(
        FieldIR(
            ordinal=index,
            name=name,
            data_type=str(silver_schema.field(name).type),
            nullable=bool(silver_schema.field(name).nullable),
            required=bool(silver_metadata.get(name, {}).get("required", True)),
            group=_group_for(name, groups),
            schema_source=schema_row["silver_pyarrow_schema"],
            description=str(silver_metadata.get(name, {}).get("description", "")),
        )
        for index, name in enumerate(silver_output, start=1)
    )

    gold_contract = cast(_JsonObject, json.loads(schema_row["gold_json_contract"]))
    gold_properties = cast(dict[str, _JsonObject], gold_contract["properties"])
    gold_names = list(gold_properties)
    gold_output = _project_fields(
        gold_names,
        groups=groups,
        include_groups=list(gold_policy["include_groups"]),
        exclude_fields=list(gold_policy["exclude_fields"]),
    )
    gold_required = set(gold_contract.get("required", []))
    gold_fields = tuple(
        FieldIR(
            ordinal=index,
            name=name,
            data_type=(
                "|".join(gold_properties[name]["type"])
                if isinstance(gold_properties[name]["type"], list)
                else str(gold_properties[name]["type"])
            ),
            nullable=bool(gold_properties[name]["nullable"]),
            required=name in gold_required,
            group=_group_for(name, groups),
            schema_source=schema_row["gold_contract_class"],
            description=str(gold_properties[name].get("description", "")),
        )
        for index, name in enumerate(gold_output, start=1)
    )
    omitted_gold = tuple(name for name in gold_names if name not in set(gold_output))

    manifest_path = (
        PROJECT_ROOT
        / "src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py"
    )
    manifest_tree = ast.parse(
        manifest_path.read_text(encoding="utf-8"), filename=str(manifest_path)
    )
    transformer_class = None
    for node in ast.walk(manifest_tree):
        if not isinstance(node, ast.Call):
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
        name_node = kwargs.get("pipeline_name")
        transformer_node = kwargs.get("transformer_class")
        if (
            isinstance(name_node, ast.Constant)
            and name_node.value == pipeline_name
            and isinstance(transformer_node, ast.Constant)
            and isinstance(transformer_node.value, str)
        ):
            transformer_class = transformer_node.value
            break
    if transformer_class is None:
        raise ValueError(
            f"Transformer registry entry not found for {pipeline_name} in {manifest_path}"
        )

    input_filter = effective["input_filter"]
    input_criteria = (
        CriterionIR(
            stage="input",
            category="input file",
            field=str(input_filter["filter_field"]),
            operator="enabled",
            value={
                "enabled": bool(input_filter["enabled"]),
                "source_path": input_filter["source_path"],
                "column_name": input_filter["column_name"],
            },
            source_key="input_filter",
            enabled=bool(input_filter["enabled"]),
        ),
    )
    explicit_exclusions = tuple(
        name
        for name in omitted_gold
        if any(fnmatch(name, pattern) for pattern in gold_policy["exclude_fields"])
    )
    unmapped_contract_fields = tuple(
        name for name in omitted_gold if name not in set(explicit_exclusions)
    )
    diagnostics: list[DiagnosticIR] = []
    if explicit_exclusions:
        diagnostics.append(
            DiagnosticIR(
                code="GOLD_CONTRACT_FIELDS_EXCLUDED_BY_POLICY",
                severity="info",
                message="Gold layer policy explicitly excludes contract fields.",
                fields=explicit_exclusions,
            )
        )
    if unmapped_contract_fields:
        diagnostics.append(
            DiagnosticIR(
                code="GOLD_CONTRACT_FIELDS_NOT_SELECTED_BY_GROUPS",
                severity="warning",
                message=(
                    "Gold contract fields are not selected by the configured column "
                    "groups; the generated output list mirrors the runtime projection."
                ),
                fields=unmapped_contract_fields,
            )
        )

    return PipelineDataflowIR(
        schema_version=IR_SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        generated_date=_source_date(),
        pipeline_name=pipeline_name,
        provider=provider,
        entity=entity,
        effective_config_sha256=_canonical_hash(effective),
        effective_config_loader=(
            "bioetl.infrastructure.config.pipeline_config_api."
            "load_pipeline_config_from_root"
        ),
        source_profile=dict(effective["source_profile"]),
        sources=_build_sources(
            provider=provider,
            entity=entity,
            schema_row=schema_row,
            transformer_class=transformer_class,
        ),
        extraction_criteria=_extraction_criteria(dict(effective["extraction_params"])),
        input_criteria=input_criteria,
        silver_criteria=_layer_criteria("silver", dict(effective["silver_filters"])),
        gold_criteria=_layer_criteria("gold", dict(effective["gold_filters"])),
        silver=LayerIR(
            name="Silver",
            schema_ref=schema_row["silver_pyarrow_schema"],
            include_groups=tuple(silver_policy["include_groups"]),
            exclude_fields=tuple(silver_policy["exclude_fields"]),
            contract_field_count=len(silver_names),
            fields=silver_fields,
            omitted_contract_fields=(),
        ),
        gold=LayerIR(
            name="Gold",
            schema_ref=schema_row["gold_contract_class"],
            include_groups=tuple(gold_policy["include_groups"]),
            exclude_fields=tuple(gold_policy["exclude_fields"]),
            contract_field_count=len(gold_names),
            fields=gold_fields,
            omitted_contract_fields=omitted_gold,
        ),
        post_processing=PostProcessingIR(
            transformer_class=transformer_class,
            declarative_steps=tuple(effective["transform"]["steps"]),
            code_defined_methods=_code_defined_methods(transformer_class),
            inspection_policy=(
                "Method presence is recorded; implementation semantics are intentionally "
                "not inferred from source code."
            ),
        ),
        dq=_build_dq(root, provider, entity),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "GENERATOR_VERSION",
    "IR_SCHEMA_VERSION",
    "CriterionIR",
    "DQSummaryIR",
    "DiagnosticIR",
    "FieldIR",
    "LayerIR",
    "PipelineDataflowIR",
    "PostProcessingIR",
    "SourceRefIR",
    "build_pipeline_dataflow_ir",
]

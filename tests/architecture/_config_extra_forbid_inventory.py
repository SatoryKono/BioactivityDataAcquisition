# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Effective ``extra`` inventory + nested-path manifest for PSC RF-001 (#12566).

Scans ``src/bioetl/infrastructure/schemas/**`` BaseModel subclasses, computes
effective ``model_config['extra']`` (local / inherited / default-ignore), and
builds:

* registry (a) migration-debt identity set (exact, sorted)
* registry (b) justified exclusions (seed; anchors finalized in RF-003)
* full runtime-root + reachable nested-path manifest with classification

This module is the generator for
``reports/quality/config-extra-forbid-inventory.json``. It does **not** migrate
``extra=forbid`` (RF-002).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
import pkgutil
import sys
import typing
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel

import bioetl.infrastructure.schemas as schemas_pkg

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_ROOT = PROJECT_ROOT / "src" / "bioetl" / "infrastructure" / "schemas"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "config-extra-forbid-inventory.json"
)
GENERATED_BY = "tests.architecture._config_extra_forbid_inventory"
SCHEMA_VERSION = 1

# Fresh-main tip when RF-001 inventory baseline was first computed.
BASELINE_SHA = "100854af874059f7a873a501518e2955f6eb5916"
ISSUE_ID = "12566"
RF_ID = "RF-001"

# Forbidden-new ceiling: exact permissive identity set at RF-001 land.
# Source of truth is this frozenset in code — NOT the regenerable JSON report.
# Regenerating ``config-extra-forbid-inventory.json`` must not refresh/widen it.
# RF-002 may shrink live migration debt below this ceiling after real forbid
# migration; it must not introduce identities outside this set.
RF001_FORBID_NEW_BASELINE_IDENTITIES: frozenset[str] = frozenset(
    {
        "bioetl.infrastructure.schemas.base_schemas_chembl.BaseApiConfig",
        "bioetl.infrastructure.schemas.base_schemas_chembl.BaseCsvExportConfig",
        "bioetl.infrastructure.schemas.base_schemas_chembl.BaseDQConfig",
        "bioetl.infrastructure.schemas.base_schemas_chembl.BaseDQThresholds",
        "bioetl.infrastructure.schemas.base_schemas_chembl.BaseMaintenanceConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseFilterColumnSchema",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseGoldColumnFilterConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseGoldFiltersConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseGoldListContainsFilterConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseGoldListLengthFilterConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseGoldRangeFilterConfig",
        "bioetl.infrastructure.schemas.base_schemas_pubchem.BaseInputFilterConfig",
        "bioetl.infrastructure.schemas.dq_report_config.BronzeDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.BronzeSinkConfig",
        "bioetl.infrastructure.schemas.dq_report_config.GoldDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.GoldSinkConfig",
        "bioetl.infrastructure.schemas.dq_report_config.SilverDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.SilverSinkConfig",
        "bioetl.infrastructure.schemas.filter_config.FilterConfigFile",
        "bioetl.infrastructure.schemas.filter_config.GoldFiltersFileConfig",
        "bioetl.infrastructure.schemas.filter_config.InputFilterFileConfig",
        "bioetl.infrastructure.schemas.filter_config.SilverFiltersFileConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common.CircuitBreakerYamlConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common.CsvExportConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.ContentHashConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.FilterColumnSchema",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.GoldColumnFilterConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.GoldFiltersConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.GoldListContainsFilterConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.GoldListLengthFilterConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.GoldRangeFilterConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.InputFilterYamlConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.MaintenanceConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.SilverFiltersConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.SinkDQReportConfig",
        "bioetl.infrastructure.schemas.pipeline_config_common_schemas.TransformConfig",
    }
)

GENERATOR_COVERED_ROOTS: dict[str, str] = {
    "bioetl.infrastructure.schemas.pipeline_config.PipelineYamlConfig": (
        "configs/_schema/pipeline.json"
    ),
    "bioetl.infrastructure.schemas.composite_config.CompositeConfigFileSchema": (
        "configs/_schema/composite.json"
    ),
    "bioetl.infrastructure.schemas.source_config.SourceYamlConfig": (
        "configs/_schema/source.json"
    ),
    "bioetl.infrastructure.schemas.dq_config.DQConfigFile": "configs/_schema/dq.json",
}

RUNTIME_ONLY_ROOTS: tuple[str, ...] = (
    "bioetl.infrastructure.schemas.filter_config.FilterConfigFile",
    "bioetl.infrastructure.schemas.dq_report_config.BronzeDQReportConfig",
    "bioetl.infrastructure.schemas.dq_report_config.SilverDQReportConfig",
    "bioetl.infrastructure.schemas.dq_report_config.GoldDQReportConfig",
    "bioetl.infrastructure.schemas.dq_report_config.BronzeSinkConfig",
    "bioetl.infrastructure.schemas.dq_report_config.SilverSinkConfig",
    "bioetl.infrastructure.schemas.dq_report_config.GoldSinkConfig",
    # load_workflow_config → WorkflowConfigFileSchema (not in generate-pipeline SCHEMAS)
    "bioetl.infrastructure.schemas.workflow_config.WorkflowConfigFileSchema",
    # load_pipeline_contract_policy → PipelineContractPolicy (entity contracts section)
    "bioetl.infrastructure.schemas.pipeline_contract_policy.PipelineContractPolicy",
)

WORKFLOW_CONFIG_ROOT = (
    "bioetl.infrastructure.schemas.workflow_config.WorkflowConfigFileSchema"
)
PIPELINE_CONTRACT_POLICY_ROOT = (
    "bioetl.infrastructure.schemas.pipeline_contract_policy.PipelineContractPolicy"
)

# Seed justified exclusions (registry b). These are NOT migration debt and MUST
# stay out of registry (a). Transfer from (a)→(b) is reclassification, not debt clear.
JUSTIFIED_EXCLUSIONS_SEED: tuple[dict[str, str], ...] = (
    {
        "identity": "bioetl.infrastructure.config._base.Settings",
        "kind": "env-settings",
        "rationale": (
            "ENV/settings surface (BaseSettings) intentionally uses extra='ignore'; "
            "not a YAML pipeline config boundary (PSC G7)."
        ),
        "anchor": "src/bioetl/infrastructure/config/_base.py",
    },
    {
        "identity": "bioetl.domain.types.identifiers.JsonDict",
        "kind": "open-dict-typealias",
        "rationale": (
            "Documented open dict alias (dict[str, Any]); unknown-key rejection is "
            "not required on the open dict itself; parent forbid-paths stay strict "
            "(PSC G6 / §3.8)."
        ),
        "anchor": "src/bioetl/domain/types/identifiers.py",
    },
    {
        "identity": "src/bioetl/infrastructure/adapters/**",
        "kind": "adapter-wire-models",
        "rationale": (
            "Upstream API response / adapter wire DTOs may tolerate extra keys; "
            "out of PSC forbid-track (PSC G8). Do not confuse with BaseApiConfig."
        ),
        "anchor": "src/bioetl/infrastructure/adapters/",
    },
)

DQ_YAML_INGRESS_IDENTITY = (
    "bioetl.infrastructure.schemas.pipeline_config_common_schemas.SinkDQReportConfig"
)
DQ_PROJECTION_IDENTITIES: frozenset[str] = frozenset(
    {
        "bioetl.infrastructure.schemas.dq_report_config.BronzeDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.SilverDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.GoldDQReportConfig",
        "bioetl.infrastructure.schemas.dq_report_config.BronzeSinkConfig",
        "bioetl.infrastructure.schemas.dq_report_config.SilverSinkConfig",
        "bioetl.infrastructure.schemas.dq_report_config.GoldSinkConfig",
    }
)
BASE_API_CONFIG_IDENTITY = (
    "bioetl.infrastructure.schemas.base_schemas_chembl.BaseApiConfig"
)


def _qualname(cls: type[Any]) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_extra_from_ast_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "extra":
                return _const_str(keyword.value)
    if isinstance(node, ast.Dict):
        for key_node, value_node in zip(node.keys, node.values, strict=False):
            if isinstance(key_node, ast.Constant) and key_node.value == "extra":
                return _const_str(value_node)
    return None


def _local_extra_declarations() -> dict[str, str | None]:
    """Map ``module.ClassName`` → locally declared ``extra`` (or None)."""
    declared: dict[str, str | None] = {}
    for path in sorted(SCHEMAS_ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        relative = path.relative_to(SCHEMAS_ROOT).with_suffix("")
        module_name = "bioetl.infrastructure.schemas." + relative.as_posix().replace(
            "/", "."
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            local: str | None = None
            for stmt in node.body:
                value: ast.AST | None = None
                targets: list[ast.AST] = []
                if isinstance(stmt, ast.Assign):
                    targets = list(stmt.targets)
                    value = stmt.value
                elif isinstance(stmt, ast.AnnAssign) and isinstance(
                    stmt.target, ast.Name
                ):
                    targets = [stmt.target]
                    value = stmt.value
                for target in targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "model_config"
                        and value is not None
                    ):
                        local = _extract_extra_from_ast_value(value)
                if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
                    for config_stmt in stmt.body:
                        if not isinstance(config_stmt, ast.Assign):
                            continue
                        for target in config_stmt.targets:
                            if isinstance(target, ast.Name) and target.id == "extra":
                                local = _const_str(config_stmt.value)
            declared[f"{module_name}.{node.name}"] = local
    return declared


def _iter_schema_basemodels() -> dict[str, type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for module_info in pkgutil.walk_packages(
        schemas_pkg.__path__, schemas_pkg.__name__ + "."
    ):
        module = importlib.import_module(module_info.name)
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseModel) or obj is BaseModel:
                continue
            if obj.__module__ != module_info.name:
                continue
            models[_qualname(obj)] = obj
    return dict(sorted(models.items()))


def _effective_extra(cls: type[BaseModel]) -> str:
    value = cls.model_config.get("extra")
    if value is None:
        return "ignore"
    return str(value)


def _declaration_source(
    local_extra: str | None,
    *,
    local_map: Mapping[str, str | None],
    cls: type[BaseModel],
) -> str:
    if local_extra is not None:
        return "local"
    for base in cls.__mro__[1:]:
        if not issubclass(base, BaseModel) or base is BaseModel:
            continue
        base_identity = _qualname(base)
        base_local = local_map.get(base_identity)
        if base_local is not None:
            return f"inherited-{base_local}"
    return "default-ignore"


def _unwrap_annotation(annotation: object) -> list[object]:
    origin = get_origin(annotation)
    args = get_args(annotation)
    union_type = getattr(typing, "Union", None)
    types_union = getattr(__import__("types"), "UnionType", None)
    if (
        origin is typing.Union
        or origin is union_type
        or (types_union is not None and isinstance(annotation, types_union))
    ):
        out: list[object] = []
        for arg in args:
            if arg is type(None):
                continue
            out.extend(_unwrap_annotation(arg))
        return out
    if origin is None:
        return [annotation]
    if origin in (list, set, tuple, dict, frozenset) or getattr(
        origin, "__name__", ""
    ) in {"list", "set", "tuple", "dict", "Annotated", "Sequence", "Mapping"}:
        out = []
        for arg in args:
            out.extend(_unwrap_annotation(arg))
        return out
    if args:
        return _unwrap_annotation(args[0])
    return [annotation]


def _is_basemodel_type(candidate: object) -> bool:
    return isinstance(candidate, type) and issubclass(candidate, BaseModel)


def _walk_nested_paths(
    model: type[BaseModel],
    *,
    prefix: str = "",
    seen: set[tuple[type[BaseModel], str]] | None = None,
) -> Iterator[tuple[str, type[BaseModel]]]:
    if seen is None:
        seen = set()
    key = (model, prefix)
    if key in seen:
        return
    seen.add(key)
    yield prefix or "$", model
    for field_name, field_info in model.model_fields.items():
        path = f"{prefix}.{field_name}" if prefix else field_name
        for candidate in _unwrap_annotation(field_info.annotation):
            if _is_basemodel_type(candidate):
                yield from _walk_nested_paths(
                    candidate,  # type: ignore[arg-type]
                    prefix=path,
                    seen=seen,
                )


def _role_for_identity(identity: str) -> str:
    if identity == DQ_YAML_INGRESS_IDENTITY:
        return "dq-yaml-ingress"
    if identity in DQ_PROJECTION_IDENTITIES:
        return "dq-layer-projection"
    if identity == BASE_API_CONFIG_IDENTITY:
        return "api-connection-config"
    if identity == WORKFLOW_CONFIG_ROOT:
        return "workflow-config-root"
    if identity == PIPELINE_CONTRACT_POLICY_ROOT:
        return "pipeline-contract-policy-root"
    if identity in GENERATOR_COVERED_ROOTS:
        return "generator-root"
    if identity in RUNTIME_ONLY_ROOTS:
        return "runtime-only-root"
    return "config-boundary"


def _classify_path(
    *,
    identity: str,
    effective: str,
    migration_debt: set[str],
    root_identity: str,
) -> str:
    if identity in {exclusion["identity"] for exclusion in JUSTIFIED_EXCLUSIONS_SEED}:
        return "justified-exclusion"
    if effective == "forbid":
        if root_identity in GENERATOR_COVERED_ROOTS and identity == root_identity:
            return "generator-covered"
        return "forbid"
    if identity in migration_debt:
        if root_identity in RUNTIME_ONLY_ROOTS and identity == root_identity:
            return "runtime-only"
        return "migration-debt"
    return "unclassified-permissive"


def build_model_rows() -> list[dict[str, object]]:
    local_map = _local_extra_declarations()
    models = _iter_schema_basemodels()
    rows: list[dict[str, object]] = []
    for identity, cls in models.items():
        local_extra = local_map.get(identity)
        effective = _effective_extra(cls)
        source = _declaration_source(local_extra, local_map=local_map, cls=cls)
        rows.append(
            {
                "identity": identity,
                "module": cls.__module__,
                "name": cls.__name__,
                "local_extra": local_extra,
                "effective_extra": effective,
                "declaration_source": source,
                "role": _role_for_identity(identity),
            }
        )
    return rows


def _counts(rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
    local_forbid = sum(1 for row in rows if row["local_extra"] == "forbid")
    local_ignore = sum(1 for row in rows if row["local_extra"] == "ignore")
    local_none = sum(1 for row in rows if row["local_extra"] is None)
    among_inherited_forbid = sum(
        1 for row in rows if row["declaration_source"] == "inherited-forbid"
    )
    among_inherited_ignore = sum(
        1 for row in rows if row["declaration_source"] == "inherited-ignore"
    )
    among_default_ignore = sum(
        1 for row in rows if row["declaration_source"] == "default-ignore"
    )
    effective_forbid = sum(1 for row in rows if row["effective_extra"] == "forbid")
    effective_ignore = sum(1 for row in rows if row["effective_extra"] == "ignore")
    return {
        "basemodel_total": len(rows),
        "local_forbid": local_forbid,
        "local_ignore": local_ignore,
        "local_none": local_none,
        "among_none_inherited_forbid": among_inherited_forbid,
        "among_none_inherited_ignore": among_inherited_ignore,
        "among_none_default_ignore": among_default_ignore,
        "effective_forbid": effective_forbid,
        "effective_ignore": effective_ignore,
    }


def _runtime_root_classes() -> dict[str, type[BaseModel]]:
    from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
    from bioetl.infrastructure.schemas.dq_config import DQConfigFile
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeDQReportConfig,
        BronzeSinkConfig,
        GoldDQReportConfig,
        GoldSinkConfig,
        SilverDQReportConfig,
        SilverSinkConfig,
    )
    from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.schemas.pipeline_contract_policy import (
        PipelineContractPolicy,
    )
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig
    from bioetl.infrastructure.schemas.workflow_config import WorkflowConfigFileSchema

    roots: dict[str, type[BaseModel]] = {
        _qualname(PipelineYamlConfig): PipelineYamlConfig,
        _qualname(CompositeConfigFileSchema): CompositeConfigFileSchema,
        _qualname(SourceYamlConfig): SourceYamlConfig,
        _qualname(DQConfigFile): DQConfigFile,
        _qualname(FilterConfigFile): FilterConfigFile,
        _qualname(BronzeDQReportConfig): BronzeDQReportConfig,
        _qualname(SilverDQReportConfig): SilverDQReportConfig,
        _qualname(GoldDQReportConfig): GoldDQReportConfig,
        _qualname(BronzeSinkConfig): BronzeSinkConfig,
        _qualname(SilverSinkConfig): SilverSinkConfig,
        _qualname(GoldSinkConfig): GoldSinkConfig,
        _qualname(WorkflowConfigFileSchema): WorkflowConfigFileSchema,
        _qualname(PipelineContractPolicy): PipelineContractPolicy,
    }
    return roots


def build_manifest(
    *,
    migration_debt: set[str],
    model_effective: Mapping[str, str],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    roots = _runtime_root_classes()
    root_rows: list[dict[str, object]] = []
    path_rows: list[dict[str, object]] = []
    for root_identity, root_cls in roots.items():
        schema_artifact = GENERATOR_COVERED_ROOTS.get(root_identity)
        coverage = "generator-covered" if schema_artifact else "runtime-only"
        root_effective = model_effective.get(root_identity, _effective_extra(root_cls))
        root_rows.append(
            {
                "identity": root_identity,
                "coverage": coverage,
                "schema_artifact": schema_artifact,
                "effective_extra": root_effective,
                "classification": _classify_path(
                    identity=root_identity,
                    effective=root_effective,
                    migration_debt=migration_debt,
                    root_identity=root_identity,
                ),
                "role": _role_for_identity(root_identity),
            }
        )
        for path, model in _walk_nested_paths(root_cls):
            identity = _qualname(model)
            effective = model_effective.get(identity, _effective_extra(model))
            path_rows.append(
                {
                    "root": root_identity,
                    "path": path,
                    "identity": identity,
                    "effective_extra": effective,
                    "classification": _classify_path(
                        identity=identity,
                        effective=effective,
                        migration_debt=migration_debt,
                        root_identity=root_identity,
                    ),
                    "role": _role_for_identity(identity),
                }
            )
    root_rows.sort(key=lambda row: str(row["identity"]))
    path_rows.sort(
        key=lambda row: (str(row["root"]), str(row["path"]), str(row["identity"]))
    )
    return root_rows, path_rows


def build_payload() -> dict[str, object]:
    rows = build_model_rows()
    model_effective = {
        str(row["identity"]): str(row["effective_extra"]) for row in rows
    }
    migration_debt = sorted(
        str(row["identity"]) for row in rows if row["effective_extra"] == "ignore"
    )
    migration_debt_set = set(migration_debt)
    reachable: set[str] = set()
    root_rows, path_rows = build_manifest(
        migration_debt=migration_debt_set,
        model_effective=model_effective,
    )
    for path_row in path_rows:
        reachable.add(str(path_row["identity"]))

    for row in rows:
        identity = str(row["identity"])
        row["reachable_from_runtime_roots"] = identity in reachable
        if identity == BASE_API_CONFIG_IDENTITY:
            row["not_wire_dto"] = True
            row["notes"] = (
                "API connection/client config (base_url/rate_limit/timeout); "
                "forbidden to auto-exclude as adapter wire (PSC §3.4)."
            )
        if identity == DQ_YAML_INGRESS_IDENTITY:
            row["notes"] = (
                "YAML/pipeline sink ingress: enabled/output_path/format only; "
                "no checks field (PSC §3.9)."
            )
        if identity in DQ_PROJECTION_IDENTITIES:
            row["notes"] = (
                "Layer-specific DQ projection DTO (may include checks); "
                "not the SinkLayerConfig.dq_report YAML ingress. Composition "
                "risk: sink_config.model_dump() → projection.model_validate."
            )

    justified = [dict(item) for item in JUSTIFIED_EXCLUSIONS_SEED]
    justified.sort(key=lambda item: item["identity"])

    forbid_new_baseline = sorted(RF001_FORBID_NEW_BASELINE_IDENTITIES)
    unknown_vs_baseline = sorted(
        set(migration_debt) - RF001_FORBID_NEW_BASELINE_IDENTITIES
    )
    if unknown_vs_baseline:
        raise RuntimeError(
            "Live effective-ignore identities outside frozen RF-001 forbid-new "
            f"baseline: {unknown_vs_baseline}"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "rf": RF_ID,
        "issue": ISSUE_ID,
        "baseline_sha": BASELINE_SHA,
        "schemas_root": "src/bioetl/infrastructure/schemas",
        "counts": _counts(rows),
        "models": rows,
        # (a) regenerable current debt — may shrink after RF-002 migration.
        "migration_debt_identities": migration_debt,
        # Frozen forbid-new ceiling (copy of RF001_FORBID_NEW_BASELINE_IDENTITIES).
        # Regenerating this JSON does not redefine the ceiling; the Python
        # frozenset is the authority. Owning tests assert against the constant.
        "forbid_new_baseline_identities": forbid_new_baseline,
        "justified_exclusions": justified,
        "runtime_roots": root_rows,
        "nested_paths": path_rows,
        "notes": {
            "dual_registries": (
                "migration_debt_identities=(a) current exact identity set; "
                "justified_exclusions=(b) seed. Transfer (a)→(b) ≠ clearing debt."
            ),
            "forbid_new_permissive": (
                "Forbid-new ceiling is RF001_FORBID_NEW_BASELINE_IDENTITIES in "
                "tests/architecture/_config_extra_forbid_inventory.py. "
                "Any new effective-ignore under schemas/** outside that frozenset "
                "fails. Regenerating the JSON report must not refresh/widen it; "
                "migration_debt_identities may shrink below the ceiling after "
                "real RF-002 forbid migration."
            ),
            "dq_yaml_ingress": (
                "SinkLayerConfig.dq_report → SinkDQReportConfig "
                "(enabled/output_path/format; no checks)."
            ),
            "base_api_config": (
                "BaseApiConfig is connection config in migration debt; not wire."
            ),
            "generator_scope": (
                "generate-pipeline emits only pipeline/composite/source/dq JSON; "
                "FilterConfigFile, dq_report_config, WorkflowConfigFileSchema, and "
                "PipelineContractPolicy roots are runtime-only."
            ),
        },
    }


def render_payload(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = render_payload(payload)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(serialized, encoding="utf-8")
    os.replace(tmp, path)


def write_inventory(path: Path = DEFAULT_JSON_OUTPUT) -> Path:
    payload = build_payload()
    atomic_write_json(path, payload)
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    payload = build_payload()
    expected = render_payload(payload)
    output_path = args.json_out
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    if args.check:
        if not output_path.exists():
            print(
                f"Missing config-extra-forbid inventory: {output_path}", file=sys.stderr
            )
            return 1
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "config-extra-forbid inventory is stale. Regenerate with:\n"
                "  .venv/bin/python -m tests.architecture._config_extra_forbid_inventory",
                file=sys.stderr,
            )
            return 1
        return 0

    atomic_write_json(output_path, payload)
    print(f"Wrote config-extra-forbid inventory: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

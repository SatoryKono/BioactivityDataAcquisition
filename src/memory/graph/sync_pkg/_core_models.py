"""Dataclass models extracted from the graph sync kernel (AUD-001 slice 1)."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

type JsonScalar = str | int | float | bool | None

type JsonValue = object

__all__ = [
    "AlertDashboardConfig",
    "AlertRuleContext",
    "AlertRuleGroupContext",
    "AlertRuleSettings",
    "AlertRunbookContext",
    "AlertTargetInputs",
    "AnalysisLabelSets",
    "ClaimLineContext",
    "ComplexityAnalysisConfig",
    "ComplexityMetrics",
    "ComplexityScoreInputs",
    "ContractMappingConfig",
    "ControlPlaneArtifactSpec",
    "EntityScope",
    "GroupedStatementFailureContext",
    "JsonScalar",
    "JsonValue",
    "NodeKey",
    "PortSurfaceDescriptor",
    "RetirementAnalysisConfig",
    "RetirementScoreInputs",
    "SchemaFieldSpec",
    "SnapshotSelection",
    "StorageSurfaceSpec",
    "SyncApplyOptions",
    "_ShapeNormalizer",
]


@dataclass(frozen=True)
class AlertDashboardConfig:
    alert_rule: dict[str, object]
    dashboard_fallbacks: dict[str, object]
    fallback_groups: dict[str, object]


@dataclass(frozen=True)
class AlertRuleContext:
    alert_name: str
    annotations: dict[str, object]
    labels: dict[str, object]


@dataclass(frozen=True)
class AlertRuleGroupContext:
    group_name: str
    rules: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class AlertRuleSettings:
    pipeline_mode: str
    pipeline_kind: str
    provider_mode: str
    contract_mode: str


@dataclass(frozen=True)
class AlertRunbookContext:
    runbook: str


@dataclass(frozen=True)
class AlertTargetInputs:
    expr: str
    dimensions: set[str]


@dataclass(frozen=True)
class AnalysisLabelSets:
    ignored_relation_types: set[str]
    runtime_labels: set[str]
    config_labels: set[str]
    doc_labels: set[str]
    test_labels: set[str]


@dataclass(frozen=True)
class ClaimLineContext:
    stripped: str
    clean_text: str


@dataclass(frozen=True)
class ComplexityAnalysisConfig:
    enabled: bool
    family_names: tuple[str, ...]
    complexity_score_threshold: int
    removable_score_threshold: int
    indirection_markers: tuple[str, ...]
    stateful_markers: tuple[str, ...]
    deprecation_markers: tuple[str, ...]
    blocker_anchor_limit: int


@dataclass(frozen=True)
class ComplexityMetrics:
    branch_count: int
    nesting_depth: int
    call_count: int
    helper_call_count: int
    abstraction_fanout: int
    api_surface_to_logic_ratio: float


@dataclass(frozen=True)
class ComplexityScoreInputs:
    indirection_markers: tuple[str, ...]
    stateful_markers: tuple[str, ...]
    deprecation_markers: tuple[str, ...]
    runtime_count: int
    config_count: int
    doc_count: int
    test_count: int
    blocked_by_current_cycle: bool


@dataclass(frozen=True)
class ContractMappingConfig:
    source_prefixes: tuple[str, ...]
    control_plane_modules: list[str]
    control_plane_runtime_modules: list[str]
    lineage_modules: list[str]
    lineage_runtime_modules: list[str]
    control_plane_docs: list[str]
    lineage_docs: list[str]
    control_plane_anchor_fields: list[str]
    lineage_anchor_fields: list[str]


@dataclass(frozen=True)
class ControlPlaneArtifactSpec:
    artifact_name: str
    summary: str
    today: str
    artifact_family: str
    artifact_kind: str
    storage_ref: str
    artifact_format: str | None = None
    key_template: str | None = None


@dataclass(frozen=True)
class EntityScope:
    provider: str | None = None
    entity: str | None = None
    pipeline_name: str | None = None


@dataclass(frozen=True)
class GroupedStatementFailureContext:
    kind: str
    group_name: str
    batch_index: int
    batch_count: int
    statement_index: int
    statement_count: int


@dataclass(frozen=True)
class NodeKey:
    label: str
    name: str


@dataclass(frozen=True)
class PortSurfaceDescriptor:
    surface_name: str
    class_name: str
    module_name: str
    source_path: str


@dataclass(frozen=True)
class RetirementAnalysisConfig:
    enabled: bool
    family_names: tuple[str, ...]
    current_cycle_age_days: int
    stale_age_days: int
    dead_score_threshold: int
    wip_markers: tuple[str, ...]
    deprecation_markers: tuple[str, ...]


@dataclass(frozen=True)
class RetirementScoreInputs:
    runtime_count: int
    config_count: int
    doc_count: int
    test_count: int
    recent_age_days: int | None
    wip_markers: list[str]
    deprecation_markers: list[str]


@dataclass(frozen=True)
class SnapshotSelection:
    only_labels: tuple[str, ...] = ()
    only_analysis_layer: bool = False
    only_retirement_layer: bool = False
    only_complexity_layer: bool = False
    only_storage_layer: bool = False
    only_runtime_evidence_layer: bool = False
    only_workflow_graph: bool = False
    only_docs_drift: bool = False

    def has_targeted_filters(self) -> bool:
        return any(
            (
                self.only_analysis_layer,
                self.only_retirement_layer,
                self.only_complexity_layer,
                self.only_storage_layer,
                self.only_runtime_evidence_layer,
                self.only_workflow_graph,
                self.only_docs_drift,
            )
        )

    def targeted_mode(self) -> bool:
        return self.has_targeted_filters() or bool(self.only_labels)

    def mode_description(self) -> str:
        if self.only_complexity_layer:
            return "complexity-layer targeted sync"
        if self.only_retirement_layer:
            return "retirement-layer targeted sync"
        if self.only_analysis_layer:
            return "analysis-layer targeted sync"
        if self.only_storage_layer:
            return "storage-layer targeted sync"
        if self.only_runtime_evidence_layer:
            return "runtime-evidence targeted sync"
        if self.only_workflow_graph:
            return "workflow-graph targeted sync"
        if self.only_docs_drift:
            return "docs-drift targeted sync"
        return "targeted sync"


@dataclass(frozen=True)
class SyncApplyOptions:
    batch_size: int
    prune_stale: bool = False
    full_reset_managed_wave: bool = False
    prune_legacy_unmanaged: bool = False


class _ShapeNormalizer(ast.NodeTransformer):
    def visit_arg(self, node: ast.arg) -> ast.arg:
        replacement = ast.arg(arg="ARG", annotation=None, type_comment=None)
        replacement.lineno = node.lineno
        replacement.col_offset = node.col_offset
        replacement.end_lineno = node.end_lineno
        replacement.end_col_offset = node.end_col_offset
        return replacement

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="VAR", ctx=node.ctx), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        value = self.visit(node.value)
        return ast.copy_location(
            ast.Attribute(value=value, attr="ATTR", ctx=node.ctx), node
        )

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if value is None or isinstance(value, bool):
            return node
        replacement: JsonScalar
        if isinstance(value, str):
            replacement = "STR"
        elif isinstance(value, (int, float, complex)):
            replacement = 0
        elif isinstance(value, bytes):
            replacement = "BYTES"
        else:
            replacement = "CONST"
        return ast.copy_location(ast.Constant(value=replacement), node)


@dataclass(frozen=True)
class SchemaFieldSpec:
    contract_ref: str | None = None
    scope: EntityScope = EntityScope()
    required_in_quality: bool | None = None
    validation_types: list[str] | None = None
    drift_classification: str | None = None
    source_storage_refs: list[str] | None = None


@dataclass(frozen=True)
class StorageSurfaceSpec:
    ref: str
    summary: str
    layer: str
    today: str
    storage_kind: str
    scope: EntityScope = EntityScope()
    format_name: str | None = None
    mode: str | None = None
    enabled: bool | None = None
    retention_days: int | None = None
    config_version: str | None = None
    quality_version: str | None = None
    partition_by: list[str] | None = None
    sort_by: list[str] | None = None
    on_schema_mismatch: str | None = None
    versioning_mode: str | None = None
    version_column: str | None = None
    current_flag_column: str | None = None
    valid_from_column: str | None = None
    valid_to_column: str | None = None
    merge_strategy: str | None = None
    semantic_properties: dict[str, JsonValue] = field(default_factory=dict)

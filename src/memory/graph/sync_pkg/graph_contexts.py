"""Graph assembly context dataclasses extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from memory.graph.sync_pkg._core_models import (
    AnalysisLabelSets,
    ComplexityMetrics,
    JsonValue,
    NodeKey,
)
from memory.graph.sync_pkg.graph_snapshot import GraphRelation, GraphSnapshot

__all__ = [
    "AlertTargetContext",
    "AnalysisAnchors",
    "CallableDescriptor",
    "ClassDescriptor",
    "ComplexityAnalysisContext",
    "CompositeOutputConfig",
    "CompositePipelineContext",
    "ContractEntryContext",
    "DuplicateFamilyConfig",
    "DuplicationExtractionContext",
    "EntityLayerFieldContext",
    "EntityPipelineContext",
    "RetirementAnalysisContext",
    "SurfaceAnchorSets",
    "SurfaceComplexityMetrics",
    "SurfaceRelationIndexes",
    "WorkflowContext",
    "WorkflowJobContext",
]


@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    title: str
    relative_path: str
    today: str
    workflow: NodeKey


@dataclass(frozen=True)
class WorkflowJobContext:
    workflow_name: str
    job_id: str
    job_name: str
    relative_path: str
    today: str
    job: NodeKey


@dataclass(frozen=True)
class EntityPipelineContext:
    provider_name: str
    entity_name: str
    pipeline_name: str
    pipeline_key: NodeKey
    entity_key: NodeKey
    config_artifact: NodeKey
    today: str
    contract_ref: str
    retention_days: int | None
    config_version: str | None
    quality_version: str | None


@dataclass(frozen=True)
class CompositePipelineContext:
    composite_name: str
    pipeline_key: NodeKey
    config_artifact: NodeKey
    today: str
    composite_version: str | None


@dataclass(frozen=True)
class AlertTargetContext:
    snapshot: GraphSnapshot
    pipeline_nodes: dict[str, NodeKey]
    provider_nodes: list[NodeKey]
    contract_nodes: dict[str, NodeKey]
    memory_mapping: dict[str, object]


@dataclass(frozen=True)
class EntityLayerFieldContext:
    payload: dict[str, object]
    surface: NodeKey
    layer_name: str
    quality_index: dict[str, dict[str, JsonValue]]
    layer_config: dict[str, object]


@dataclass(frozen=True)
class CompositeOutputConfig:
    merge_payload: dict[str, object]
    output_payload: dict[str, object]
    group_fields: list[tuple[str, str]]
    source_storage_refs: list[str]
    schema_fields_by_storage: dict[str, dict[str, NodeKey]]


@dataclass(frozen=True)
class ContractEntryContext:
    root: Path
    registry_path: Path
    today: str
    contract_ref: str
    contract: NodeKey
    raw_entry: dict[str, object]


@dataclass
class DuplicationExtractionContext:
    snapshot: GraphSnapshot
    root: Path
    today: str
    config: dict[str, object]
    class_descriptors: dict[NodeKey, ClassDescriptor] = field(default_factory=dict)
    callable_descriptors: dict[NodeKey, CallableDescriptor] = field(
        default_factory=dict
    )
    class_name_index: dict[str, list[NodeKey]] = field(default_factory=dict)


@dataclass(frozen=True)
class DuplicateFamilyConfig:
    name: str
    roots: tuple[str, ...]
    package_family: str
    promotion_targets: tuple[NodeKey, ...]
    excluded_paths: tuple[str, ...] = ()


@dataclass
class CallableDescriptor:
    node_key: NodeKey
    family_name: str
    package_family: str
    source_path: str
    callable_name: str
    parent_class: str | None
    surface_kind: str
    ast_shape_hash: str
    signature_hash: str
    ast_node_count: int
    semantic_tags: tuple[str, ...]


@dataclass
class ClassDescriptor:
    node_key: NodeKey
    family_name: str
    package_family: str
    source_path: str
    class_name: str
    base_names: tuple[str, ...]
    method_names: tuple[str, ...]


@dataclass(frozen=True)
class SurfaceRelationIndexes:
    incoming: dict[NodeKey, list[GraphRelation]]
    outgoing: dict[NodeKey, list[GraphRelation]]
    declared_children: dict[NodeKey, list[NodeKey]]


@dataclass(frozen=True)
class AnalysisAnchors:
    runtime: tuple[NodeKey, ...]
    config: tuple[NodeKey, ...]
    docs: tuple[NodeKey, ...]
    tests: tuple[NodeKey, ...]


# Canonical names used by complexity/retirement analysis surfaces (PD-C01).
type SurfaceAnchorSets = AnalysisAnchors
type SurfaceComplexityMetrics = ComplexityMetrics


@dataclass
class RetirementAnalysisContext:
    label_sets: AnalysisLabelSets
    indexes: SurfaceRelationIndexes
    today_date: date
    text_cache: dict[str, str] = field(default_factory=dict)
    age_cache: dict[str, int | None] = field(default_factory=dict)
    family_cache: dict[str, DuplicateFamilyConfig | None] = field(default_factory=dict)
    family_names: set[str] = field(default_factory=set)


@dataclass
class ComplexityAnalysisContext:
    label_sets: AnalysisLabelSets
    indexes: SurfaceRelationIndexes
    text_cache: dict[str, str] = field(default_factory=dict)
    family_cache: dict[str, DuplicateFamilyConfig | None] = field(default_factory=dict)
    family_names: set[str] = field(default_factory=set)

"""Freeze and restore merge collaborators that differ between composite families."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
    build_merge_execution_request,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.field_groups import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
    current_protein_class_target_type_mapping,
)
from bioetl.domain.types import JsonDict


def freeze_target_mapping() -> JsonDict:
    """Capture the exact initialized mapping consumed by target dependency joins."""
    mapping = current_protein_class_target_type_mapping()
    return {
        "mapping_version": mapping.mapping_version,
        "entries": [asdict(entry) for entry in mapping.entries],
        "non_counting_classes": sorted(mapping.non_counting_classes),
    }


def restore_target_mapping(payload: JsonDict) -> ProteinClassTargetTypeMappingData:
    """Restore sealed lookup data without consulting mutable configuration files."""
    return ProteinClassTargetTypeMappingData(
        mapping_version=payload["mapping_version"],
        entries=tuple(
            ProteinClassTopLevelMappingEntry(**row) for row in payload["entries"]
        ),
        non_counting_classes=frozenset(payload["non_counting_classes"]),
    )


def freeze_field_groups(registry: FieldGroupRegistry | None) -> JsonDict:
    """Serialize the actual registry used by the live merge, including defaults."""
    if registry is None:
        return {"registry": None}
    return {
        "registry": {
            "groups": [asdict(group) for group in registry.groups],
            "provider_order": list(registry.provider_order),
            "default_group": registry.default_group.value,
        }
    }


def restore_field_groups(payload: JsonDict) -> FieldGroupRegistry | None:
    """Reconstruct the captured registry without reading mutable YAML files."""
    value = payload["registry"]
    if value is None:
        return None
    groups = tuple(
        FieldGroupDefinition(
            group_id=FieldGroupId(group["group_id"]),
            display_name=group["display_name"],
            include_in_gold=group["include_in_gold"],
            fields=tuple(
                FieldMapping(
                    base_name=item["base_name"],
                    provider_columns=tuple(item["provider_columns"]),
                    group=FieldGroupId(item["group"]),
                )
                for item in group["fields"]
            ),
        )
        for group in value["groups"]
    )
    return FieldGroupRegistry(
        groups=groups,
        provider_order=tuple(value["provider_order"]),
        default_group=FieldGroupId(value["default_group"]),
    )


def output_table_name(path: str, layer: str) -> str:
    """Resolve the same logical table name used by the production merge writer."""
    normalized = path.replace("\\", "/")
    marker = f"{layer}/"
    return normalized.split(marker, 1)[1] if marker in normalized else normalized


def required_replay_tables(request: MergeExecutionRequest) -> frozenset[str]:
    """Declare consumed inputs independently of whether reads succeeded."""
    required = {request.seed_table}
    required.update(
        item.silver_table or f"silver/{item.pipeline}"
        for item in request.enrichers
        if (result := request.enrichment_results.get(item.pipeline)) is not None
        and result.contributes_merge_input
    )
    required.update(_successful_dependency_tables(request))
    return frozenset(required)


def _successful_dependency_tables(request: MergeExecutionRequest) -> frozenset[str]:
    """Select dependency inputs only when their captured result succeeded."""
    return frozenset(
        item.silver_table or f"silver/{item.pipeline}"
        for item in request.dependencies or ()
        if (dependency := (request.dependency_results or {}).get(item.pipeline))
        is not None
        and dependency.status == DependencyStatus.SUCCESS
    )


def freeze_merge_request(request: MergeExecutionRequest) -> JsonDict:
    """Serialize resolved selections and statuses for symmetric offline restoration."""
    if request.metadata_timestamp is None:
        raise ValueError("composite_replay_request_timestamp_missing")
    return {
        "seed_table": request.seed_table,
        "seed_pipeline": request.seed_pipeline,
        "metadata_timestamp": request.metadata_timestamp.isoformat(),
        "enrichers": [item.pipeline for item in request.enrichers],
        "outcomes": {
            name: result.status.value
            for name, result in request.enrichment_results.items()
        },
        "dependencies": [item.pipeline for item in request.dependencies or ()],
        "dependency_outcomes": {
            name: result.status.value
            for name, result in (request.dependency_results or {}).items()
        },
    }


def restore_merge_request(
    config: CompositeConfig, payload: JsonDict, run_id: str
) -> MergeExecutionRequest:
    """Restore explicit stage selections and statuses from the bound request."""
    return build_merge_execution_request(
        seed_table=payload["seed_table"],
        seed_pipeline=payload["seed_pipeline"],
        enrichers=tuple(
            item for item in config.enrichers if item.pipeline in payload["enrichers"]
        ),
        enrichment_results={
            name: EnrichmentResult(name, EnrichmentStatus(status))
            for name, status in payload["outcomes"].items()
        },
        dependencies=tuple(
            item
            for item in config.dependencies
            if item.pipeline in payload.get("dependencies", [])
        ),
        dependency_results={
            name: DependencyResult(name, DependencyStatus(status))
            for name, status in payload.get("dependency_outcomes", {}).items()
        },
        run_id=run_id,
        metadata_timestamp=datetime.fromisoformat(payload["metadata_timestamp"]),
    )

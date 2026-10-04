"""Freeze and restore merge collaborators that differ between composite families."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
    build_merge_execution_request,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)

from bioetl.domain.composite.field_groups import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
)
from bioetl.domain.types import JsonDict


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
    required.update(
        item.silver_table or f"silver/{item.pipeline}"
        for item in request.dependencies or ()
        if (dependency := (request.dependency_results or {}).get(item.pipeline))
        is not None
        and dependency.status == DependencyStatus.SUCCESS
    )
    return frozenset(required)


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

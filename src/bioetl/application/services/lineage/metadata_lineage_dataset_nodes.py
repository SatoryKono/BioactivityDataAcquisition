"""Dataset and schema lineage node builders."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.services.lineage.metadata_assemblers_helpers import (
    _resolve_source_batch_ids,
)
from bioetl.domain.behavior.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.lineage import DatasetRef, LineageNodeRef, LineageNodeType, SchemaRef

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeMetadataInput,
        GoldMetadataInput,
        SilverMetadataInput,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.run_context import RunContext


def bronze_batch_node_from_input(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageNodeRef:
    """Build Bronze-batch node from Bronze metadata input."""
    return LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id=f"bronze_batch:{input_data.batch_id}",
        label=f"{run_context.provider}.{run_context.entity}",
        attributes={
            "batch_id": str(input_data.batch_id),
            "provider": run_context.provider,
            "entity": run_context.entity,
            "output_path": input_data.output_path,
            "record_count": input_data.record_count,
            "compressed_size": input_data.compressed_size,
        },
    )


def _bronze_batch_node_from_result(ref: BronzeWriteResult) -> LineageNodeRef:
    """Build Bronze-batch node from Bronze write result."""
    provider, entity = ref.provider_entity
    return LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id=f"bronze_batch:{ref.batch_id}",
        label=ref.table_name,
        attributes={
            "batch_id": str(ref.batch_id),
            "provider": provider,
            "entity": entity,
            "table_name": ref.table_name,
            "relative_path": ref.relative_path,
            "absolute_path": ref.absolute_path,
            "record_count": ref.record_count,
            "compressed_size": ref.compressed_size,
            "checksum_blake2": ref.checksum_blake2,
        },
    )


def bronze_batch_nodes_for_silver(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> list[LineageNodeRef]:
    """Build Bronze upstream nodes for Silver lineage."""
    nodes: dict[str, LineageNodeRef] = {}
    for batch_id in _resolve_source_batch_ids(input_data):
        nodes.setdefault(
            batch_id,
            LineageNodeRef(
                node_type=LineageNodeType.BRONZE_BATCH,
                node_id=f"bronze_batch:{batch_id}",
                label=f"{run_context.provider}.{run_context.entity}",
                attributes={
                    "batch_id": batch_id,
                    "provider": run_context.provider,
                    "entity": run_context.entity,
                },
            ),
        )
    if input_data.bronze_refs is None:
        return [nodes[node_id] for node_id in sorted(nodes)]
    bronze_refs = cast("list[BronzeWriteResult]", input_data.bronze_refs)
    for ref in bronze_refs:
        nodes[str(ref.batch_id)] = _bronze_batch_node_from_result(ref)
    return [nodes[node_id] for node_id in sorted(nodes)]


def silver_dataset_node(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> LineageNodeRef:
    """Build persisted Silver dataset node."""
    dataset = DatasetRef(
        layer="silver",
        logical_name=f"{run_context.provider}.{run_context.entity}",
        version=input_data.version_after,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return dataset.to_node_ref()


def gold_dataset_node(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> LineageNodeRef:
    """Build persisted Gold dataset node."""
    dataset = DatasetRef(
        layer="gold",
        logical_name=input_data.table_name,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return dataset.to_node_ref()


def silver_source_nodes(input_data: GoldMetadataInput) -> list[LineageNodeRef]:
    """Build Silver upstream dataset nodes for Gold lineage."""
    if not input_data.silver_refs:
        return []
    return [
        DatasetRef(
            layer="silver",
            logical_name=ref.table_name,
            version=ref.delta_version,
            path=ref.table_path,
        ).to_node_ref()
        for ref in sorted(
            input_data.silver_refs,
            key=lambda item: (item.table_name, item.delta_version, item.table_path),
        )
    ]


def schema_node(input_data: GoldMetadataInput) -> LineageNodeRef | None:
    """Build schema node when Gold schema metadata is available."""
    schema_info = extract_schema_metadata(input_data.schema_inspection)
    if schema_info.contract_path is None and not schema_info.columns:
        return None
    return SchemaRef(
        contract_path=schema_info.contract_path or "inline_schema",
        version=schema_info.version,
        validation_mode=schema_info.validation,
        dataset_name=None,
    ).to_node_ref()


__all__ = [
    "bronze_batch_node_from_input",
    "bronze_batch_nodes_for_silver",
    "gold_dataset_node",
    "schema_node",
    "silver_dataset_node",
    "silver_source_nodes",
]

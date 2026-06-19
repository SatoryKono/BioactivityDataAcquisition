"""Concrete lineage-node builders."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.lineage.metadata_lineage_anchor_nodes import (
    manifest_edges,
    manifest_node,
    run_node,
    source_request_node,
    source_system_node,
)
from bioetl.application.services.lineage.metadata_lineage_dataset_nodes import (
    bronze_batch_node_from_input,
    bronze_batch_nodes_for_silver,
    gold_dataset_node,
    schema_node,
    silver_dataset_node,
    silver_source_nodes,
)
from bioetl.application.services.lineage.metadata_lineage_fragment_ids import (
    build_fragment_id,
    build_semantic_fragment_id,
    dedupe_nodes,
)
from bioetl.application.services.lineage.metadata_lineage_transform_nodes import (
    resolve_transform_metadata,
    transform_edges,
    transform_nodes,
)


def fragment_timestamp(*values: datetime | None) -> datetime:
    """Resolve one stable fragment timestamp through the legacy facade seam."""
    for value in values:
        if value is not None:
            return value
    return current_utc_time()


__all__ = [
    "bronze_batch_node_from_input",
    "bronze_batch_nodes_for_silver",
    "build_fragment_id",
    "build_semantic_fragment_id",
    "dedupe_nodes",
    "fragment_timestamp",
    "gold_dataset_node",
    "manifest_edges",
    "manifest_node",
    "resolve_transform_metadata",
    "run_node",
    "schema_node",
    "silver_dataset_node",
    "silver_source_nodes",
    "source_request_node",
    "source_system_node",
    "transform_edges",
    "transform_nodes",
]

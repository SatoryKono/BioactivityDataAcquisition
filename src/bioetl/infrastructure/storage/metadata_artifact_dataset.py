"""Dataset-reference helpers for metadata artifact publication."""

from __future__ import annotations

from bioetl.domain.lineage import DatasetRef
from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata


def derive_dataset_ref(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str | None:
    """Return canonical dataset ref when the sidecar represents a dataset artifact."""
    artifact_id = str(getattr(metadata.output, "artifact_id", "") or "").strip()
    if artifact_id.startswith(("bronze_batch:", "silver:", "gold:")):
        return artifact_id
    layer = str(getattr(metadata, "layer", ""))
    if layer == "silver":
        output_ext = getattr(metadata, "output_ext", None)
        dataset_ref = DatasetRef(
            layer="silver",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            version=getattr(output_ext, "delta_version_after", None),
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        )
        return str(dataset_ref.node_id)
    if layer == "gold":
        dataset_ref = DatasetRef(
            layer="gold",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        )
        return str(dataset_ref.node_id)
    return None


def resolve_lineage_log_context(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> dict[str, object]:
    """Resolve optional lineage anchors for control-plane and log emission."""
    return {
        "dataset_ref": derive_dataset_ref(metadata),
        "lineage_fragment_id": metadata.output.lineage_fragment_id,
    }


__all__ = ["derive_dataset_ref", "resolve_lineage_log_context"]

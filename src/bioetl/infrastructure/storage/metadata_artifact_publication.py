"""Artifact-publication helpers for metadata sidecar writers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.domain.models.metadata import (
    BronzeMetadata,
    GoldMetadata,
    SilverMetadata,
)
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.storage.metadata_artifact_dataset import (
    resolve_lineage_log_context as _resolve_lineage_log_context,
)
from bioetl.infrastructure.storage.metadata_artifact_details import (
    build_artifact_publication_details as _build_artifact_publication_details,
)
from bioetl.infrastructure.storage.metadata_artifact_metrics import (
    record_artifact_publication_metric as _record_artifact_publication_metric,
)
from bioetl.infrastructure.storage.metadata_artifact_metrics import (
    require_artifact_publication_identifier as _require_artifact_publication_identifier,
)

ArtifactPublicationRecorder = Callable[[str, str, dict[str, object] | None], object]


def _record_artifact_publication(
    *,
    recorder: ArtifactPublicationRecorder | None,
    metrics: MetricsPort | None,
    layer: str,
    base_path: str | Path,
    metadata_path: str,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> None:
    """Emit the optional control-plane artifact publication callback."""
    if recorder is None:
        _record_artifact_publication_metric(
            metrics=metrics,
            metadata=metadata,
            layer=layer,
            status="disabled",
        )
        return
    manifest_id = _require_artifact_publication_identifier(
        raw_value=metadata.runtime.manifest_id,
        missing_message=(
            "Control-plane artifact publication requires metadata.runtime.manifest_id"
        ),
        metrics=metrics,
        metadata=metadata,
        layer=layer,
    )
    artifact_id = _require_artifact_publication_identifier(
        raw_value=metadata.output.artifact_id,
        missing_message=(
            "Control-plane artifact publication requires metadata.output.artifact_id"
        ),
        metrics=metrics,
        metadata=metadata,
        layer=layer,
    )
    details = _build_artifact_publication_details(
        metadata_path=metadata_path,
        metadata=metadata,
        manifest_id=manifest_id,
        artifact_id=artifact_id,
        layer=layer,
    )
    try:
        recorder(layer, str(Path(base_path).resolve()), details)
    except RuntimeError:
        _record_artifact_publication_metric(
            metrics=metrics,
            metadata=metadata,
            layer=layer,
            status="failed",
        )
        raise
    _record_artifact_publication_metric(
        metrics=metrics,
        metadata=metadata,
        layer=layer,
        status="success",
    )


__all__ = [
    "ArtifactPublicationRecorder",
    "_record_artifact_publication",
    "_resolve_lineage_log_context",
]

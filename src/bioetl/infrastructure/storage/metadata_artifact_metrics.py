"""Metric helpers for metadata artifact publication."""

from __future__ import annotations

from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata
from bioetl.domain.ports import MetricsPort


def artifact_publication_metric_labels(
    *,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
    status: str,
) -> dict[str, str]:
    """Build canonical labels for artifact-publication outcome metrics."""
    return {
        "pipeline": metadata.pipeline.name,
        "stage": layer,
        "status": status,
    }


def record_artifact_publication_metric(
    *,
    metrics: MetricsPort | None,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
    status: str,
) -> None:
    """Emit one bounded artifact-publication status counter when metrics exist."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_output_artifact_publication_events_total",
        1,
        artifact_publication_metric_labels(
            metadata=metadata,
            layer=layer,
            status=status,
        ),
    )


def require_artifact_publication_identifier(
    *,
    raw_value: object | None,
    missing_message: str,
    metrics: MetricsPort | None,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
) -> str:
    """Return a required publication identifier or raise a contract error."""
    value = str(raw_value or "").strip()
    if value:
        return value
    record_artifact_publication_metric(
        metrics=metrics,
        metadata=metadata,
        layer=layer,
        status="failed",
    )
    raise RuntimeError(missing_message)


__all__ = [
    "record_artifact_publication_metric",
    "require_artifact_publication_identifier",
]

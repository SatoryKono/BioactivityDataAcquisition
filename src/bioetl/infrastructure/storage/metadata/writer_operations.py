"""Internal request/telemetry helpers for metadata sidecar writes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort


METADATA_FILENAME = "_metadata.yaml"


@dataclass(frozen=True, slots=True)
class _PreparedMetadataWrite:
    """Prepared metadata sidecar write request."""

    metadata_path: Path
    yaml_content: str
    pipeline_label: str


@dataclass(frozen=True, slots=True)
class _MetadataWriteRequest:
    """Named request for a metadata sidecar write."""

    base_path: str | Path
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata
    layer: str
    table_name: str | None = None
    flat_structure: bool = False
    provider: str | None = None
    entity: str | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedMetadataTarget:
    """Resolved target path and pipeline label for one metadata sidecar."""

    metadata_path: Path
    pipeline_label: str


@dataclass(frozen=True, slots=True)
class _MetadataWriteTelemetryContext:
    """Shared telemetry fields for metadata sidecar writes."""

    layer: str
    provider: str | None
    pipeline: str


@dataclass(frozen=True, slots=True)
class _PreparedMetadataWriteOperation:
    """Prepared write operation with shared telemetry/log context."""

    prepared_write: _PreparedMetadataWrite
    telemetry_context: _MetadataWriteTelemetryContext
    run_id: str


@dataclass(slots=True)
class _MetadataWriteRetryState:
    """Mutable retry count shared with the atomic-write callback."""

    count: int = 0


@dataclass(frozen=True, slots=True)
class _MetadataWriteFinalTelemetry:
    """Resolved final telemetry labels for one metadata write outcome."""

    event_name: str
    severity: str
    retry_count: int
    final_reason: str


def _get_metadata_filename(provider: str | None, entity: str | None) -> str:
    """Return `{provider}_{entity}_metadata.yaml` or the default filename."""

    if provider and entity:
        return f"{provider}_{entity}_metadata.yaml"
    return METADATA_FILENAME


def _resolve_metadata_target(request: _MetadataWriteRequest) -> _ResolvedMetadataTarget:
    """Resolve the file path and pipeline label for a metadata write."""

    path = Path(request.base_path)
    provider = request.provider
    entity = request.entity

    if provider and entity:
        metadata_path = path / _get_metadata_filename(provider, entity)
    elif request.flat_structure and request.table_name:
        metadata_path = path / f"{request.table_name}_metadata.yaml"
    else:
        metadata_path = path / METADATA_FILENAME

    pipeline_label = request.table_name or (
        f"{provider}.{entity}" if provider and entity else f"{request.layer}_metadata"
    )
    return _ResolvedMetadataTarget(
        metadata_path=metadata_path,
        pipeline_label=pipeline_label,
    )


def _serialize_metadata_yaml(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str:
    """Serialize the metadata model to canonical YAML content."""

    canonical_metadata = type(metadata).model_validate(
        metadata.model_dump(
            mode="python",
            by_alias=True,
            exclude_computed_fields=True,
            warnings="none",
        )
    )
    serialized_yaml = yaml.safe_dump(
        canonical_metadata.model_dump(mode="json", by_alias=True),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return str(serialized_yaml)


def _build_prepared_metadata_write(
    request: _MetadataWriteRequest,
    target: _ResolvedMetadataTarget,
) -> _PreparedMetadataWrite:
    """Build the prepared metadata payload after resolving the target path."""
    return _PreparedMetadataWrite(
        metadata_path=target.metadata_path,
        yaml_content=_serialize_metadata_yaml(request.metadata),
        pipeline_label=target.pipeline_label,
    )


def _build_metadata_write_telemetry_context(
    request: _MetadataWriteRequest,
    prepared_write: _PreparedMetadataWrite,
) -> _MetadataWriteTelemetryContext:
    """Build the shared telemetry context for one metadata write operation."""
    return _MetadataWriteTelemetryContext(
        layer=request.layer,
        provider=request.provider,
        pipeline=prepared_write.pipeline_label,
    )


def _build_prepared_metadata_write_operation(
    *,
    prepared_write: _PreparedMetadataWrite,
    telemetry_context: _MetadataWriteTelemetryContext,
    run_id: str,
) -> _PreparedMetadataWriteOperation:
    """Build operation payload with runtime-specific state."""

    return _PreparedMetadataWriteOperation(
        prepared_write=prepared_write,
        telemetry_context=telemetry_context,
        run_id=run_id,
    )


def _prepare_metadata_write_operation(
    request: _MetadataWriteRequest,
) -> _PreparedMetadataWriteOperation:
    """Resolve target/payload/telemetry and package one executable operation."""

    target = _resolve_metadata_target(request)
    prepared_write = _build_prepared_metadata_write(request, target)
    telemetry_context = _build_metadata_write_telemetry_context(
        request,
        prepared_write=prepared_write,
    )
    return _build_prepared_metadata_write_operation(
        prepared_write=prepared_write,
        telemetry_context=telemetry_context,
        run_id=request.metadata.runtime.run_id,
    )


def _emit_retry_telemetry(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    context: _MetadataWriteTelemetryContext,
    attempt: int,
    delay_seconds: float,
    reason: str,
) -> None:
    """Emit telemetry event for metadata atomic-write retry."""

    logger.warning(
        "metadata_atomic_replace_retry",
        layer=context.layer,
        provider=context.provider,
        pipeline=context.pipeline,
        attempt=attempt,
        delay_seconds=delay_seconds,
        reason=reason,
    )
    if metrics is not None:
        metrics.increment_counter(
            "bioetl_metadata_write_retries_total",
            1,
            {
                "layer": context.layer,
                "provider": context.provider or "storage",
                "pipeline": context.pipeline,
                "reason": reason,
            },
        )


def _emit_final_telemetry(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    context: _MetadataWriteTelemetryContext,
    outcome: _MetadataWriteFinalTelemetry,
) -> None:
    """Emit telemetry for final metadata write outcome."""

    if outcome.severity == "error":
        logger.error(
            outcome.event_name,
            layer=context.layer,
            provider=context.provider,
            pipeline=context.pipeline,
            retry_count=outcome.retry_count,
            final_reason=outcome.final_reason,
        )
    else:
        logger.info(
            outcome.event_name,
            layer=context.layer,
            provider=context.provider,
            pipeline=context.pipeline,
            retry_count=outcome.retry_count,
            final_reason=outcome.final_reason,
        )
    if metrics is not None:
        metrics.increment_counter(
            "bioetl_metadata_write_outcomes_total",
            1,
            {
                "layer": context.layer,
                "provider": context.provider or "storage",
                "pipeline": context.pipeline,
                "status": "failed" if outcome.severity == "error" else "succeeded",
                "final_reason": outcome.final_reason,
            },
        )


def _build_metadata_write_final_telemetry(
    *,
    status: str,
    retry_count: int,
    final_reason: str,
) -> _MetadataWriteFinalTelemetry:
    """Resolve the canonical final telemetry outcome for one metadata write."""

    return _MetadataWriteFinalTelemetry(
        event_name="metadata_write_failed"
        if status == "failed"
        else "metadata_write_completed",
        severity="error" if status == "failed" else "info",
        retry_count=retry_count,
        final_reason=final_reason,
    )


def _build_retry_callback(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    context: _MetadataWriteTelemetryContext,
    retry_state: _MetadataWriteRetryState,
) -> Callable[[int, float, OSError], None]:
    """Build the retry callback used by atomic_write_text."""

    def on_retry(attempt: int, delay_seconds: float, error: OSError) -> None:
        retry_state.count = attempt
        _emit_retry_telemetry(
            logger=logger,
            metrics=metrics,
            context=context,
            attempt=attempt,
            delay_seconds=delay_seconds,
            reason=str(getattr(error, "errno", "os_error")),
        )

    return on_retry


def _emit_atomic_write_final_telemetry(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    context: _MetadataWriteTelemetryContext,
    retry_state: _MetadataWriteRetryState,
    status: str,
    final_reason: str,
) -> None:
    """Emit the final metadata-write event from the accumulated retry state."""

    outcome = _build_metadata_write_final_telemetry(
        status=status,
        retry_count=retry_state.count,
        final_reason=final_reason,
    )
    _emit_final_telemetry(
        logger=logger,
        metrics=metrics,
        context=context,
        outcome=outcome,
    )

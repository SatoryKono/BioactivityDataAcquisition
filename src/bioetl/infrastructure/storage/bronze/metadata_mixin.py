"""Thin BronzeWriter wrappers around pure metadata builders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.types import BatchID, JsonDict, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata

    class _BronzeLineageSidecarCoordinator(Protocol):
        def create_bronze_lineage_sidecar(
            self,
            *,
            provider: str,
            entity: str,
            batch_id: BatchID,
            ingestion_ts: datetime,
        ) -> dict[str, str]: ...


class BronzeWriterMetadataMixin:
    """Mixin with bronze metadata construction helpers."""

    @staticmethod
    def _build_legacy_bronze_lineage_sidecar(
        *,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Build the baseline `.meta.json` payload without coordinator services."""
        return {
            "run_id": str(run_id),
            "run_type": run_type.value,
            "ingestion_ts": effective_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
            "sidecar_truth_boundary": "legacy_lineage_projection_non_authoritative",
            "authoritative_replay_artifacts": (
                "run_manifest,lineage_fragment,layer_metadata,"
                "effective_config_artifact"
            ),
        }

    @staticmethod
    def _raise_legacy_bronze_metadata_builder_error(
        *,
        provider: str,
        entity: str,
        output_path: str,
    ) -> None:
        raise RuntimeError(
            "MetadataCoordinator with create_bronze_metadata_bundle is required "
            "for Bronze metadata publication: "
            f"provider={provider}, entity={entity}, relative_path={output_path}"
        )

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Build metadata dict for lineage tracking.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            effective_ts: UTC ingestion timestamp to embed in the metadata.
            provider: Data provider name.
            entity: Entity type name.
            batch_id: Unique identifier for this write batch.

        Returns:
            Dictionary of string metadata fields for Bronze lineage tracking.
        """
        coordinator = cast(
            "_BronzeLineageSidecarCoordinator | None",
            getattr(self, "_metadata_coordinator", None),
        )
        create_sidecar = (
            None
            if coordinator is None
            else getattr(coordinator, "create_bronze_lineage_sidecar", None)
        )
        if callable(create_sidecar):
            return create_sidecar(
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                ingestion_ts=effective_ts,
            )
        return self._build_legacy_bronze_lineage_sidecar(
            run_id=run_id,
            run_type=run_type,
            effective_ts=effective_ts,
            provider=provider,
            entity=entity,
            batch_id=batch_id,
        )

    def _build_full_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeMetadata:
        """Build rich BronzeMetadata for sidecar file.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            provider: Data provider name.
            entity: Entity type name.
            batch_id: Unique identifier for this write batch.
            record_count: Number of records written.
            compressed_size: Compressed byte size of the written file.
            output_path: Relative path of the output file for metadata reference.
            started_at: UTC datetime when the write operation started.
            completed_at: UTC datetime when the write operation completed.
            duration_seconds: Total write duration in seconds.
            source_metadata: Optional provider metadata to embed in the sidecar.

        Returns:
            BronzeMetadata instance populated with runtime, pipeline, source, and output fields.
        """
        del (
            batch_id,
            run_id,
            run_type,
            record_count,
            compressed_size,
            started_at,
            completed_at,
            duration_seconds,
            source_metadata,
        )
        self._raise_legacy_bronze_metadata_builder_error(
            provider=provider,
            entity=entity,
            output_path=output_path,
        )
        raise AssertionError("unreachable")

    def _build_bronze_metadata_payload(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None,
    ) -> JsonDict:  # Any: bronze metadata model fields are heterogeneous
        """Build Bronze metadata constructor payload.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            provider: Data provider name.
            entity: Entity type name.
            record_count: Number of records written.
            compressed_size: Compressed byte size of the written file.
            output_path: Relative path of the output file for metadata reference.
            started_at: UTC datetime when the write operation started.
            completed_at: UTC datetime when the write operation completed.
            duration_seconds: Total write duration in seconds.
            source_metadata: Optional provider metadata to embed in the sidecar.

        Returns:
            Dictionary of constructor keyword arguments for BronzeMetadata.
        """
        del (
            run_id,
            run_type,
            record_count,
            compressed_size,
            started_at,
            completed_at,
            duration_seconds,
            source_metadata,
        )
        self._raise_legacy_bronze_metadata_builder_error(
            provider=provider,
            entity=entity,
            output_path=output_path,
        )
        raise AssertionError("unreachable")


__all__ = ["BronzeWriterMetadataMixin"]

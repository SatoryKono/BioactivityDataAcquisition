"""Metadata builder component implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.configs import QualityControlConfig
from bioetl.domain.models import RunContext
from bioetl.domain.ports.output import MetadataBuilderPort


class MetadataBuilder(MetadataBuilderPort):
    """Builder for deterministic run metadata.

    This component constructs metadata dictionaries without
    knowledge of how they will be serialized or persisted.
    """

    def build_run_metadata(
        self,
        context: RunContext,
        result: WriteResult,
        *,
        qc_artifacts: list[Path] | None = None,
        qc_checksums: dict[str, str] | None = None,
        qc_config: QualityControlConfig | None = None,
    ) -> dict[str, Any]:
        """Build metadata for a completed pipeline run.

        Args:
            context: Run context with execution details.
            result: Write result with path and checksum.
            qc_artifacts: List of QC artifact paths.
            qc_checksums: Checksums for QC artifacts.
            qc_config: QC configuration used.

        Returns:
            Metadata dictionary with run details.
        """
        qc_artifacts = qc_artifacts or []
        qc_checksums = qc_checksums or {}
        qc_config = qc_config or QualityControlConfig()

        files = [result.path.name]
        files.extend(path.name for path in qc_artifacts)

        meta = self._build_base_metadata(
            context, row_count=result.row_count, include_metadata=False
        )
        meta.update(
            {
                "checksum": result.checksum,
                # For backward compatibility and explicitness
                "hash": result.checksum,
                "files": sorted(files),
                "checksums": {
                    result.path.name: result.checksum,
                    **qc_checksums,
                },
                "qc_artifacts": {
                    path.name: {
                        "path": path.name,
                        "checksum": qc_checksums.get(path.name),
                    }
                    for path in sorted(qc_artifacts, key=lambda p: p.name)
                },
                "qc_config": {
                    "enable_quality_report": qc_config.enable_quality_report,
                    "enable_correlation_report": qc_config.enable_correlation_report,
                    "min_coverage": qc_config.min_coverage,
                },
            }
        )
        meta.update(context.metadata)
        return meta

    def build_dry_run_metadata(
        self, context: RunContext, row_count: int
    ) -> dict[str, Any]:
        """Build metadata for a dry-run execution.

        Args:
            context: Run context.
            row_count: Number of rows that would be written.

        Returns:
            Metadata dictionary for dry run.
        """
        return self._build_base_metadata(
            context, row_count=row_count, dry_run=True, include_metadata=True
        )

    def _build_base_metadata(
        self,
        context: RunContext,
        *,
        row_count: int,
        dry_run: bool = False,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Build base metadata dictionary.

        Args:
            context: Run context.
            row_count: Number of rows.
            dry_run: Whether this is a dry run.
            include_metadata: Whether to include user metadata from context.

        Returns:
            Base metadata dictionary.
        """
        meta: dict[str, Any] = {
            "run_id": str(context.run_id),
            "entity": str(context.entity_name),
            "provider": str(context.provider),
            "timestamp": context.started_at.isoformat(),
            "hash_version": "v1_blake2b_256",
            "row_count": row_count,
        }

        if dry_run:
            meta["dry_run"] = True

        if include_metadata:
            meta.update(context.metadata)

        return meta


__all__ = ["MetadataBuilder"]

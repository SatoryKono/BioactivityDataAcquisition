"""Helper functions for metadata assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_assembler_support import (
    PipelineMetadataBuilderProtocol,
    RuntimeMetadataBuilderProtocol,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    augment_dq_summary_with_composite_cv as _augment_dq_summary_with_composite_cv,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_dataset_content_hash as _build_dataset_content_hash,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_gold_dq_summary as _build_gold_dq_summary,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_runtime_duration as _build_runtime_duration,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_silver_dq_summary as _build_silver_dq_summary,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    coerce_rule_provenance_mappings as _coerce_rule_provenance_mappings,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    extract_composite_output_extension as _extract_composite_output_ext,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    normalize_rule_provenance_entries as _normalize_rule_provenance_entries,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_composite_list_metadata as _parse_composite_list,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_composite_status_metadata as _parse_composite_status,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_lineage_created_at_metadata as _parse_lineage_created_at,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_bronze_paths as _resolve_bronze_paths,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_record_count as _resolve_record_count,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_source_batch_ids as _resolve_source_batch_ids,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_transform_metadata as _resolve_transform_metadata,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_artifact_id as _build_gold_artifact_id,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_lineage as _build_gold_lineage,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_output as _build_gold_output_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_scd as _build_gold_scd,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_artifact_id as _build_silver_artifact_id,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_delta as _build_silver_delta,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_lineage as _build_silver_lineage,
)
from bioetl.application.services.lineage.metadata_output_support import (
    resolve_gold_source_tables as _resolve_gold_source_tables,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BaseOutputMetadata, CompositeOutputExt
    from bioetl.domain.ports import GoldMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


def _build_gold_output(
    *,
    run_context: RunContext | None = None,
    input_data: GoldMetadataInput,
    record_count: int,
    composite_ext: CompositeOutputExt | None,
) -> BaseOutputMetadata:
    """Build Gold base output metadata with the legacy content-hash policy."""
    return _build_gold_output_support(
        run_context=run_context,
        input_data=input_data,
        record_count=record_count,
        composite_ext=composite_ext,
        content_hash=(
            _build_dataset_content_hash(
                provider=run_context.provider,
                records=input_data.records,
            )
            if run_context is not None
            else None
        ),
    )


__all__ = [
    "PipelineMetadataBuilderProtocol",
    "RuntimeMetadataBuilderProtocol",
    "_augment_dq_summary_with_composite_cv",
    "_build_dataset_content_hash",
    "_build_gold_artifact_id",
    "_build_gold_dq_summary",
    "_build_gold_lineage",
    "_build_gold_output",
    "_build_gold_scd",
    "_build_runtime_duration",
    "_build_silver_artifact_id",
    "_build_silver_delta",
    "_build_silver_dq_summary",
    "_build_silver_lineage",
    "_coerce_rule_provenance_mappings",
    "_extract_composite_output_ext",
    "_normalize_rule_provenance_entries",
    "_parse_composite_list",
    "_parse_composite_status",
    "_parse_lineage_created_at",
    "_resolve_bronze_paths",
    "_resolve_gold_source_tables",
    "_resolve_record_count",
    "_resolve_source_batch_ids",
    "_resolve_transform_metadata",
]

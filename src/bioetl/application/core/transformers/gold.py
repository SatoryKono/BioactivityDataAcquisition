"""Default Gold Transformer.

Implements the default logic for Gold layer transformation:
- Filtering based on configured gold_filters
- Excluding internal/forensic fields
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.context import PipelineContext


class DefaultGoldTransformer:
    """Default implementation of GoldTransformerPort.

    Uses pipeline configuration to filter records and excludes standard internal fields.
    """

    # Fields to exclude from Gold layer (JSON strings retained only in Silver)
    # Moved from BasePipeline
    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            # Molecule JSON fields (Silver forensic only)
            "molecule_hierarchy",
            "molecule_properties",
            "molecule_structures",
            "molecule_synonyms",
            "cross_references",
            "atc_classifications",
            # Internal metadata fields (Silver only)
            "entity_id",
            "content_hash",
            "_run_type",
            "_source_batch_id",
        }
    )

    def __init__(self, config: PipelineConfig):
        """Initialize with pipeline configuration."""
        self._gold_filters = config.gold_filters

    def should_process(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Determine if a Silver record should be written to Gold.

        Uses gold_filters from config if configured.
        """
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        return self._gold_filters.should_include(record)

    def transform(
        self, _context: PipelineContext, silver_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform Silver record for Gold layer.

        Removes excluded fields.
        """
        return {
            k: v
            for k, v in silver_record.items()
            if k not in self.GOLD_EXCLUDE_FIELDS
        }

"""ChEMBL Document Similarity Transformer.

Transforms Bronze records to Silver format (DocumentSimilarity entity inflation).
Handles composite key normalization (doc1 < doc2 lexicographically).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import DocumentSimilarity
from bioetl.domain.types import EntityID

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class DocumentSimilarityTransformer(BaseTransformer):
    """Transforms ChEMBL bronze document similarity records to silver.

    Handles:
    - Composite key normalization (doc1 < doc2 lexicographically)
    - Tanimoto coefficient validation ([0, 1] range)
    - Content hash generation for deduplication
    """

    def __init__(
        self,
        provider: str = "chembl",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ) -> None:
        """Initialize DocumentSimilarity transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider, tracer=tracer, metrics=metrics, gold_filters=gold_filters
        )

    def _normalize_pair(self, doc1: str, doc2: str) -> tuple[str, str]:
        """Normalize document pair to ensure doc1 < doc2 lexicographically.

        This ensures deterministic storage of the symmetric similarity matrix
        (only upper triangle is stored).

        Args:
            doc1: First document ChEMBL ID.
            doc2: Second document ChEMBL ID.

        Returns:
            Tuple (smaller_id, larger_id) in lexicographic order.

        """
        if doc1 <= doc2:
            return (doc1, doc2)
        return (doc2, doc1)

    def _validate_tanimoto(self, value: Any) -> float | None:
        """Validate and normalize Tanimoto coefficient.

        Tanimoto similarity must be in [0, 1] range.
        NaN/Inf values are converted to None.

        Args:
            value: Raw Tanimoto value from API.

        Returns:
            Valid Tanimoto coefficient or None if invalid/missing.

        """
        if value is None:
            return None
        try:
            float_val = float(value)
            # Handle NaN/Inf as NULL
            if math.isnan(float_val) or math.isinf(float_val):
                return None
            # Validate range [0, 1]
            if float_val < 0 or float_val > 1:
                return None
            # Round to 10 decimal places for determinism
            return round(float_val, 10)
        except (ValueError, TypeError):
            return None

    def _generate_composite_entity_id(self, doc1: str, doc2: str) -> EntityID:
        """Generate entity ID for composite key.

        Format: chembl:{doc1}_{doc2}

        Args:
            doc1: Normalized document 1 ChEMBL ID (smaller).
            doc2: Normalized document 2 ChEMBL ID (larger).

        Returns:
            EntityID in format 'chembl:CHEMBL1_CHEMBL2'.

        """
        return EntityID(f"{self.provider}:{doc1}_{doc2}")

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform document similarity bronze record to silver.

        Steps:
        1. Extract and validate document ChEMBL IDs
        2. Normalize pair order (doc1 < doc2)
        3. Skip self-similarity (doc1 == doc2)
        4. Validate Tanimoto coefficients
        5. Generate entity_id and content_hash
        6. Create domain entity and convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from ChEMBL API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Extract document IDs
        doc1_raw = record.get("document_1_chembl_id")
        doc2_raw = record.get("document_2_chembl_id")

        if not doc1_raw or not doc2_raw:
            return None

        doc1_str = str(doc1_raw).strip()
        doc2_str = str(doc2_raw).strip()

        if not doc1_str or not doc2_str:
            return None

        # 2. Normalize pair order
        doc1_normalized, doc2_normalized = self._normalize_pair(doc1_str, doc2_str)

        # 3. Skip self-similarity
        if doc1_normalized == doc2_normalized:
            return None

        # 4. Validate and normalize Tanimoto coefficients
        mol_tani = self._validate_tanimoto(record.get("mol_tani"))
        tid_tani = self._validate_tanimoto(record.get("tid_tani"))

        # 5. Prepare business data for content hash
        business_data = {
            "document_1_chembl_id": doc1_normalized,
            "document_2_chembl_id": doc2_normalized,
            "mol_tani": mol_tani,
            "tid_tani": tid_tani,
        }

        # 6. Generate entity ID and content hash
        entity_id = self._generate_composite_entity_id(doc1_normalized, doc2_normalized)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 7. Create domain entity
        entity = self._create_entity(
            DocumentSimilarity,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 8. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

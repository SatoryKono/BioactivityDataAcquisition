"""ChEMBL Document Similarity Transformer.

Transforms Bronze records to Silver format (DocumentSimilarity entity).
Computes derived Tanimoto metrics (avg_tani, max_tani).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.application.core.field_specs import normalize_pmid
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentSimilarity
from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class DocumentSimilarityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL document similarity records.

    Computes derived metrics:
    - avg_tani: average of tid_tani and mol_tani
    - max_tani: maximum of tid_tani and mol_tani
    """

    entity_class = DocumentSimilarity
    primary_id_field = "sim_id"

    HASH_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_index",
            "_content_hash",
            # Exclude derived fields from hash
            "avg_tani",
            "max_tani",
        }
    )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract DocumentSimilarity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated sim_id value.

        Returns:
            Dictionary of DocumentSimilarity business fields.

        """
        # Extract and validate Tanimoto coefficients
        tid_tani = safe_float(record.get("tid_tani"))
        mol_tani = safe_float(record.get("mol_tani"))

        # Compute derived Tanimoto metrics
        avg_tani: float | None = None
        max_tani: float | None = None

        if tid_tani is not None and mol_tani is not None:
            avg_tani = round((tid_tani + mol_tani) / 2, 6)
            max_tani = round(max(tid_tani, mol_tani), 6)
        elif tid_tani is not None:
            avg_tani = round(tid_tani, 6)
            max_tani = round(tid_tani, 6)
        elif mol_tani is not None:
            avg_tani = round(mol_tani, 6)
            max_tani = round(mol_tani, 6)

        return {
            # Primary key
            "sim_id": int(primary_id),
            # Foreign keys
            "doc_1": safe_int(record.get("doc_1")),
            "doc_2": safe_int(record.get("doc_2")),
            # PubMed identifiers (normalized to string)
            "pubmed_id1": normalize_pmid(record.get("pubmed_id1")),
            "pubmed_id2": normalize_pmid(record.get("pubmed_id2")),
            # Tanimoto coefficients
            "tid_tani": tid_tani,
            "mol_tani": mol_tani,
            # Derived metrics
            "avg_tani": avg_tani,
            "max_tani": max_tani,
        }

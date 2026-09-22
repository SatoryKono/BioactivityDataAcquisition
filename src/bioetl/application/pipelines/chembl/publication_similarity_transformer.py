"""ChEMBL Publication Similarity Transformer.

Transforms Bronze records to Silver format (ChemblPublicationSimilarity entity).
Computes derived Tanimoto metrics (avg_tani, max_tani).

.. versionchanged:: 2.0.0
    Renamed from document_similarity_transformer to publication_similarity_transformer (ADR-024).
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["PublicationSimilarityTransformer"]


from typing import TYPE_CHECKING

from bioetl.application.core.field_specs import normalize_pmid
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.entities import ChemblPublicationSimilarity
from bioetl.domain.schemas.chembl.similarity_pair import is_public_document_id
from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, PrimaryId


class PublicationSimilarityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL publication similarity records.

    Computes derived metrics:
    - avg_tani: average of tid_tani and mol_tani
    - max_tani: maximum of tid_tani and mol_tani

    .. versionchanged:: 2.0.0
        Renamed from DocumentSimilarityTransformer (ADR-024).
    """

    entity_class = ChemblPublicationSimilarity
    primary_id_field = "sim_id"

    def _prepare_record(self, record: BronzeRecord) -> BronzeRecord:
        """Keep public API identities separate from legacy internal document IDs."""
        if record.get("sim_id") is not None:
            return record
        pair = tuple(record.get(f"document_{n}_chembl_id") for n in (1, 2))
        if not all(map(is_public_document_id, pair)) or pair[0] == pair[1]:
            return record  # Required-key validation quarantines malformed records.
        # Similarity is symmetric. Scores are observations, not part of identity.
        first, second = sorted(str(value) for value in pair)
        identity = deterministic_uuid(
            "chembl.publication_similarity.public_pair.v1",
            {"first": first, "second": second},
        ).int
        return {**record, "sim_id": (identity & ((1 << 63) - 1)) or 1}

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract PublicationSimilarity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated sim_id value.

        Returns:
            Dictionary of ChemblPublicationSimilarity business fields.

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
            "publication_id1": record.get("document_1_chembl_id"),
            "publication_id2": record.get("document_2_chembl_id"),
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

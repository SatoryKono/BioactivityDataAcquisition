"""ChEMBL bioactivity domain entities.

Contains Activity (deprecated alias for Bioactivity) and Assay entities.

Migration Note:
    The `Activity` class is deprecated in favor of `Bioactivity`.
    Use `from bioetl.domain.entities import Bioactivity` for new code.
    The `Activity` alias will be removed after 14 days.

Field Classification:
    - REQUIRED: Validated in __post_init__, will raise ValueError if empty
    - API-OPTIONAL: May or may not be present in API response, defaults to None
    - COMPUTED: Derived from other fields, may be None if source data missing
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import (
    Bioactivity,
    BioactivityState,
)

__all__ = [
    "Activity",
    "Assay",
    "Bioactivity",
    "BioactivityState",
]


class Activity(Bioactivity):
    """Deprecated alias for Bioactivity.

    .. deprecated:: 1.0.0
        Use :class:`Bioactivity` instead. This alias will be removed in 14 days.

    This class exists for backward compatibility during migration.
    All functionality is inherited from Bioactivity.

    Example:
        >>> # Old code (deprecated):
        >>> from bioetl.domain.entities import Activity
        >>> activity = Activity(...)  # Will emit DeprecationWarning

        >>> # New code (recommended):
        >>> from bioetl.domain.entities import Bioactivity
        >>> bioactivity = Bioactivity(...)
    """

    def __init__(self, **kwargs: Any) -> None:
        warnings.warn(
            "Activity is deprecated, use Bioactivity instead. "
            "This alias will be removed in 14 days.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)


@dataclass(frozen=True, kw_only=True)
class Assay(BaseEntity):
    """Represents a bioassay definition (ChEMBL Assay).

    Contains all fields from ChEMBL assay API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/assay
    """

    # Primary identifier
    assay_chembl_id: str

    # Core identifiers
    target_chembl_id: str | None = None
    document_chembl_id: str | None = None
    cell_chembl_id: str | None = None
    tissue_chembl_id: str | None = None
    src_id: int | None = None
    src_assay_id: str | None = None
    aidx: str | None = None

    # Assay classification
    assay_type: str | None = None
    assay_type_description: str | None = None
    assay_category: str | None = None
    assay_test_type: str | None = None
    assay_group: str | None = None

    # Biological context
    assay_organism: str | None = None
    assay_tax_id: int | None = None
    assay_cell_type: str | None = None
    assay_tissue: str | None = None
    assay_strain: str | None = None
    assay_subcellular_fraction: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_format: str | None = None
    bao_label: str | None = None

    # Description and confidence
    description: str | None = None
    confidence_score: int | None = None
    confidence_description: str | None = None
    relationship_type: str | None = None
    relationship_description: str | None = None

    # Additional metadata
    assay_pref_name: str | None = None  # Preferred assay name (if available)
    score: float | None = None  # Assay score (distinct from confidence_score)

    # Variant information (flattened from ChEMBL API nested structure)
    variant_accession: str | None = None  # UniProt accession
    variant_isoform: str | None = None  # Isoform identifier
    variant_mutation: str | None = None  # Mutation description (e.g., V600E)
    variant_organism: str | None = None  # Organism name
    variant_sequence: str | None = None  # Amino acid sequence
    variant_tax_id: int | None = None  # NCBI Taxonomy ID
    # Forensic: original JSON
    variant_sequence_json: str | None = None

    # Complex fields (stored as JSON strings)
    assay_classifications: str | None = None  # JSON string of list
    assay_parameters: str | None = None  # JSON string of list

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.assay_chembl_id:
            raise ValueError("Assay ChEMBL ID is required")
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
            raise ValueError(
                f"Confidence score must be 0-9, got {self.confidence_score}"
            )

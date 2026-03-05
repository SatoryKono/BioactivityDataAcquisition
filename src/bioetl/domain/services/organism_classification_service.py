"""Organism classification service for assay data normalization and filtering.

Wraps the pure classification functions from ``bioetl.domain.mapping.organism_classification``
into a stateless domain service that supports:

- Single-record classification
- Batch classification with field enrichment
- Filtering records by cellularity type
- Classification statistics for diagnostics

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from bioetl.domain.mapping.organism_classification import (
    OrganismClassificationResult,
    classify_organism,
    normalize_organism_name,
)
from bioetl.domain.types import CellularityType, JsonDict

__all__ = [
    "ClassificationStats",
    "OrganismClassificationService",
]

# Default field names matching ChEMBL assay schema
_DEFAULT_ORGANISM_FIELD: Final[str] = "assay_organism"
_DEFAULT_TAXONOMY_ID_FIELD: Final[str] = "assay_tax_id"

# Output fields added during enrichment
_OUT_CELLULARITY: Final[str] = "organism_class"
_OUT_NORMALIZED_ORGANISM: Final[str] = "normalized_organism"
_OUT_CLASSIFICATION_SOURCE: Final[str] = "classification_source"
CellularityFilterStrategy = Callable[[CellularityType | None], bool]


@dataclass(frozen=True, slots=True)
class ClassificationStats:
    """Aggregated classification statistics for a batch of records.

    Attributes:
        total: Total records classified.
        acellular: Count of acellular organisms (viruses, phages).
        unicellular: Count of unicellular organisms (bacteria, archaea, protists).
        multicellular: Count of multicellular organisms (animals, plants, fungi).
        unresolved: Count of records that could not be classified.
        conflict_count: Count of records where taxonomy_id and name disagree.
    """

    total: int
    acellular: int
    unicellular: int
    multicellular: int
    unresolved: int
    conflict_count: int

    @property
    def resolved_count(self) -> int:
        """Number of successfully classified records."""
        return self.total - self.unresolved

    @property
    def resolution_rate(self) -> float:
        """Fraction of records successfully classified (0.0–1.0)."""
        if self.total == 0:
            return 0.0
        return self.resolved_count / self.total


@dataclass(frozen=True, slots=True)
class OrganismClassificationService:
    """Domain service for organism cellularity classification.

    Provides classification, enrichment, and filtering of assay records
    based on organism cellularity (acellular / unicellular / multicellular).

    This service is stateless and thread-safe. All methods are pure functions
    that delegate to ``classify_organism`` from the mapping module.

    Attributes:
        organism_field: Record field containing organism name.
        taxonomy_id_field: Record field containing NCBI taxonomy ID.

    Example:
        >>> service = OrganismClassificationService()
        >>> result = service.classify("Homo sapiens", 9606)
        >>> result.organism_class
        <CellularityType.MULTICELLULAR: 'multicellular'>

        >>> records = [{"assay_organism": "Homo sapiens", "assay_tax_id": 9606}]
        >>> enriched = service.enrich_records(records)
        >>> enriched[0]["organism_class"]
        'multicellular'
    """

    organism_field: str = _DEFAULT_ORGANISM_FIELD
    taxonomy_id_field: str = _DEFAULT_TAXONOMY_ID_FIELD

    # ------------------------------------------------------------------
    # Single-record classification
    # ------------------------------------------------------------------

    def classify(
        self,
        organism_name: str | None,
        taxonomy_id: int | str | None = None,
    ) -> OrganismClassificationResult:
        """Classify a single organism by name and/or taxonomy ID.

        Args:
            organism_name: Raw organism name (e.g., "Homo sapiens").
            taxonomy_id: NCBI Taxonomy ID (int or string).

        Returns:
            Classification result with cellularity type and diagnostics.
        """
        return classify_organism(organism_name, taxonomy_id)

    def get_cellularity(
        self,
        organism_name: str | None,
        taxonomy_id: int | str | None = None,
    ) -> CellularityType | None:
        """Get cellularity type for an organism (convenience shortcut).

        Returns:
            CellularityType or None if unresolved.

        Args:
            organism_name: Name of the organism.
            taxonomy_id: Identifier for taxonomy.
        """
        return self.classify(organism_name, taxonomy_id).organism_class

    def normalize_name(self, organism_name: str | None) -> str | None:
        """Normalize organism name for consistent lookup.

        Delegates to ``normalize_organism_name``: lowercases, strips
        parenthetical annotations, resolves aliases.

        Args:
            organism_name: Raw organism name.

        Returns:
            Normalized name, or None if input is None/empty.
        """
        return normalize_organism_name(organism_name)

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def classify_records(
        self,
        records: list[JsonDict],  # Any: untyped organism taxonomy data
    ) -> list[
        tuple[
            JsonDict,  # Any: record values are heterogeneous
            OrganismClassificationResult,
        ]
    ]:
        """Classify a batch of records, pairing each with its result.

        Args:
            records: List of assay record dicts.

        Returns:
            List of (record, classification_result) tuples.
        """
        return [(record, self._classify_record(record)) for record in records]

    def enrich_records(
        self,
        records: list[JsonDict],  # Any: untyped organism taxonomy data
    ) -> list[JsonDict]:  # Any: untyped organism taxonomy data
        """Enrich records with classification fields.

        Adds ``organism_class``, ``normalized_organism``, and
        ``classification_source`` fields to each record.

        Does NOT mutate the original records; returns new dicts.

        Args:
            records: List of assay record dicts.

        Returns:
            New list of enriched record dicts.
        """
        return [self._enrich_single(record) for record in records]

    def _enrich_single(
        self,
        record: JsonDict,  # Any: record values are heterogeneous
    ) -> JsonDict:  # Any: untyped organism taxonomy data
        """Enrich a single record with classification fields."""
        result = self._classify_record(record)
        enriched = {**record}
        enriched[_OUT_CELLULARITY] = (
            result.organism_class.value if result.organism_class else None
        )
        enriched[_OUT_NORMALIZED_ORGANISM] = result.normalized_organism
        enriched[_OUT_CLASSIFICATION_SOURCE] = result.source
        return enriched

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_by_cellularity(
        self,
        records: list[JsonDict],  # Any: untyped organism taxonomy data
        *,
        include: set[CellularityType] | None = None,
        exclude: set[CellularityType] | None = None,
        keep_unresolved: bool = True,
    ) -> list[JsonDict]:  # Any: untyped organism taxonomy data
        """Filter records by organism cellularity type.

        Exactly one of ``include`` or ``exclude`` should be provided.
        If both are None, all records pass through.

        Args:
            records: List of assay record dicts.
            include: If set, only keep records matching these types.
            exclude: If set, drop records matching these types.
            keep_unresolved: Whether to keep records that couldn't be
                classified. Defaults to True (conservative).

        Returns:
            Filtered list of records.

        Example:
            >>> service = OrganismClassificationService()
            >>> human = [{"assay_organism": "Homo sapiens", "assay_tax_id": 9606}]
            >>> virus = [{"assay_organism": "HIV-1", "assay_tax_id": 11676}]
            >>> service.filter_by_cellularity(
            ...     human + virus,
            ...     include={CellularityType.MULTICELLULAR},
            ... )
            [{'assay_organism': 'Homo sapiens', 'assay_tax_id': 9606}]
        """
        strategy = self._build_filter_strategy(
            include=include,
            exclude=exclude,
            keep_unresolved=keep_unresolved,
        )
        filtered: list[JsonDict] = []  # Any: untyped organism taxonomy data
        for record in records:
            result = self._classify_record(record)
            if strategy(result.organism_class):
                filtered.append(record)
        return filtered

    def _build_filter_strategy(
        self,
        *,
        include: set[CellularityType] | None,
        exclude: set[CellularityType] | None,
        keep_unresolved: bool,
    ) -> CellularityFilterStrategy:
        """Build filter strategy for include/exclude/unresolved policy."""
        if include is not None:
            return self._include_strategy(include, keep_unresolved)
        if exclude is not None:
            return self._exclude_strategy(exclude, keep_unresolved)
        return self._pass_all_strategy(keep_unresolved)

    @staticmethod
    def _include_strategy(
        include: set[CellularityType],
        keep_unresolved: bool,
    ) -> CellularityFilterStrategy:
        """Return include-only filter strategy."""

        def strategy(cellularity: CellularityType | None) -> bool:
            """Accept cellularity if it is in the include set."""
            if cellularity is None:
                return keep_unresolved
            return cellularity in include

        return strategy

    @staticmethod
    def _exclude_strategy(
        exclude: set[CellularityType],
        keep_unresolved: bool,
    ) -> CellularityFilterStrategy:
        """Return exclusion filter strategy."""

        def strategy(cellularity: CellularityType | None) -> bool:
            """Reject cellularity if it is in the exclude set."""
            if cellularity is None:
                return keep_unresolved
            return cellularity not in exclude

        return strategy

    @staticmethod
    def _pass_all_strategy(keep_unresolved: bool) -> CellularityFilterStrategy:
        """Return strategy when neither include nor exclude is provided."""

        def strategy(cellularity: CellularityType | None) -> bool:
            """Accept all resolved cellularity values."""
            if cellularity is None:
                return keep_unresolved
            return True

        return strategy

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def compute_stats(
        self,
        results: list[OrganismClassificationResult],
    ) -> ClassificationStats:
        """Compute classification statistics from a batch of results.

        Args:
            results: List of classification results (from ``classify_records``).

        Returns:
            Aggregated statistics.
        """
        counts: dict[CellularityType | None, int] = {
            CellularityType.ACELLULAR: 0,
            CellularityType.UNICELLULAR: 0,
            CellularityType.MULTICELLULAR: 0,
            None: 0,
        }
        conflict_count = 0

        for r in results:
            counts[r.organism_class] = counts.get(r.organism_class, 0) + 1
            if r.source_conflict:
                conflict_count += 1

        return ClassificationStats(
            total=len(results),
            acellular=counts[CellularityType.ACELLULAR],
            unicellular=counts[CellularityType.UNICELLULAR],
            multicellular=counts[CellularityType.MULTICELLULAR],
            unresolved=counts[None],
            conflict_count=conflict_count,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_record(
        self,
        record: JsonDict,  # Any: record values are heterogeneous
    ) -> OrganismClassificationResult:  # Any: untyped organism taxonomy data
        """Extract fields and classify a single record."""
        organism = record.get(self.organism_field)
        taxonomy_id = record.get(self.taxonomy_id_field)
        return classify_organism(organism, taxonomy_id)

"""Organism classifier for assay data normalization and filtering."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.mapping.organism_classification import (
    OrganismClassificationResult,
    classify_organism,
    normalize_organism_name,
)
from bioetl.domain.services.organism_classification_service_filtering import (
    build_filter_strategy,
)
from bioetl.domain.services.organism_classification_service_models import (
    _DEFAULT_ORGANISM_FIELD,
    _DEFAULT_TAXONOMY_ID_FIELD,
    _OUT_CELLULARITY,
    _OUT_CLASSIFICATION_SOURCE,
    _OUT_NORMALIZED_ORGANISM,
    ClassificationStats,
)
from bioetl.domain.types import CellularityType, JsonDict

__all__ = [
    "ClassificationStats",
    "OrganismClassificationService",
    "OrganismClassifier",
]


@dataclass(frozen=True, slots=True)
class OrganismClassifier:
    """Classifier for organism cellularity."""

    organism_field: str = _DEFAULT_ORGANISM_FIELD
    taxonomy_id_field: str = _DEFAULT_TAXONOMY_ID_FIELD

    def classify(
        self,
        organism_name: str | None,
        taxonomy_id: int | str | None = None,
    ) -> OrganismClassificationResult:
        """Classify a single organism by name and/or taxonomy ID.

        Args:
            organism_name: Scientific or common organism name, or None.
            taxonomy_id: NCBI taxonomy ID as integer or string. Defaults to None.

        Returns:
            OrganismClassificationResult with cellularity and classification details.
        """
        return classify_organism(organism_name, taxonomy_id)

    def get_cellularity(
        self,
        organism_name: str | None,
        taxonomy_id: int | str | None = None,
    ) -> CellularityType | None:
        """Get cellularity type for an organism (convenience shortcut).

        Args:
            organism_name: Scientific or common organism name, or None.
            taxonomy_id: NCBI taxonomy ID as integer or string. Defaults to None.

        Returns:
            CellularityType enum value if classified, or None if unknown.
        """
        return self.classify(organism_name, taxonomy_id).organism_class

    def normalize_name(self, organism_name: str | None) -> str | None:
        """Normalize organism name for consistent lookup.

        Args:
            organism_name: Raw organism name string or None.

        Returns:
            Normalized organism name, or None if input is None or empty.
        """
        return normalize_organism_name(organism_name)

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
            records: List of record dictionaries containing organism and taxonomy fields.

        Returns:
            List of (record, classification_result) tuples in input order.
        """
        return [(record, self._classify_record(record)) for record in records]

    def enrich_records(
        self,
        records: list[JsonDict],  # Any: untyped organism taxonomy data
    ) -> list[JsonDict]:  # Any: untyped organism taxonomy data
        """Enrich records with classification fields.

        Args:
            records: List of record dictionaries to enrich with organism classification.

        Returns:
            New list of record dictionaries with added cellularity and normalized-organism fields.
        """
        return [self._enrich_single(record) for record in records]

    def _enrich_single(
        self,
        record: JsonDict,  # Any: record values are heterogeneous
    ) -> JsonDict:  # Any: untyped organism taxonomy data
        result = self._classify_record(record)
        enriched = {**record}
        enriched[_OUT_CELLULARITY] = (
            result.organism_class.value if result.organism_class else None
        )
        enriched[_OUT_NORMALIZED_ORGANISM] = result.normalized_organism
        enriched[_OUT_CLASSIFICATION_SOURCE] = result.source
        return enriched

    def filter_by_cellularity(
        self,
        records: list[JsonDict],  # Any: untyped organism taxonomy data
        *,
        include: set[CellularityType] | None = None,
        exclude: set[CellularityType] | None = None,
        keep_unresolved: bool = True,
    ) -> list[JsonDict]:  # Any: untyped organism taxonomy data
        """Filter records by organism cellularity type.

        Args:
            records: List of record dicts containing organism and taxonomy fields.
            include: If provided, only records whose cellularity is in this set are kept.
            exclude: If provided, records whose cellularity is in this set are removed.
            keep_unresolved: If True, records with unknown cellularity are retained.
                Defaults to True.

        Returns:
            Filtered list of record dicts matching the cellularity criteria.
        """
        strategy = build_filter_strategy(
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

    def compute_stats(
        self,
        results: list[OrganismClassificationResult],
    ) -> ClassificationStats:
        """Compute classification statistics from a batch of results.

        Args:
            results: List of OrganismClassificationResult objects from classify_records.

        Returns:
            ClassificationStats with counts by cellularity type and conflict count.
        """
        counts: dict[CellularityType | None, int] = {
            CellularityType.ACELLULAR: 0,
            CellularityType.UNICELLULAR: 0,
            CellularityType.MULTICELLULAR: 0,
            None: 0,
        }
        conflict_count = 0
        for result in results:
            counts[result.organism_class] = counts.get(result.organism_class, 0) + 1
            if result.source_conflict:
                conflict_count += 1
        return ClassificationStats(
            total=len(results),
            acellular=counts[CellularityType.ACELLULAR],
            unicellular=counts[CellularityType.UNICELLULAR],
            multicellular=counts[CellularityType.MULTICELLULAR],
            unresolved=counts[None],
            conflict_count=conflict_count,
        )

    def _classify_record(
        self,
        record: JsonDict,  # Any: record values are heterogeneous
    ) -> OrganismClassificationResult:  # Any: untyped organism taxonomy data
        """Extract fields and classify a single record."""
        organism = record.get(self.organism_field)
        taxonomy_id = record.get(self.taxonomy_id_field)
        return classify_organism(organism, taxonomy_id)


# Deprecated compatibility alias retained during ADR-041 migration.
OrganismClassificationService = OrganismClassifier

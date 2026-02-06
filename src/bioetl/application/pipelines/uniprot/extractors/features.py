"""
Feature extractor for UniProt XML data.
"""

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.domain.schemas.uniprot.protein import FeatureSchema


class FeatureExtractor(AbstractExtractor):
    """
    Extracts feature information from UniProt XML data.

    Maps UniProt 'feature' elements to the FeatureSchema.
    Features include regions, sites, bonds, and other annotations on the sequence.
    """

    def extract(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract features from a UniProt entry.

        Args:
            entry: The UniProt entry dictionary

        Returns:
            List of feature dictionaries
        """
        features = []
        if not (feature_list := entry.get("feature")):
            return features

        # Handle single feature (dict) vs list of features
        if isinstance(feature_list, dict):
            feature_list = [feature_list]

        for feat in feature_list:
            if not isinstance(feat, dict):
                continue

            if feature_data := self._process_feature(feat):
                features.append(feature_data)

        return features

    def _process_feature(self, feat: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single feature entry."""
        # Get location data
        location = feat.get("location", {})
        if not location:
            return None

        # Extract positions
        start, end = self._extract_location(location)

        # Build feature dictionary
        return {
            "type": feat.get("@type"),
            "description": self._clean_description(feat.get("@description")),
            "status": feat.get("@status"),
            "id": feat.get("@id"),
            "start": start,
            "end": end,
            "original": self._extract_original(location),
            "variation": self._extract_variation(location),
            "evidence": self._extract_evidence(feat),
            "ref": feat.get("@ref"),
        }

    def _extract_location(
        self, location: dict[str, Any]
    ) -> tuple[int | None, int | None]:
        """Extract start and end positions from location."""
        start = None
        end = None

        # Try exact position
        if position := location.get("position"):
            if pos := position.get("@position"):
                try:
                    start = int(pos)
                    end = int(pos)
                except (ValueError, TypeError):
                    pass
        else:
            # Try range
            if begin := location.get("begin"):
                try:
                    start = int(begin.get("@position"))
                except (ValueError, TypeError):
                    pass
            if end_elem := location.get("end"):
                try:
                    end = int(end_elem.get("@position"))
                except (ValueError, TypeError):
                    pass

        return start, end

    def _clean_description(self, description: str | None) -> str | None:
        """Clean description text."""
        return ExtractorUtils.clean_text(description)

    def _extract_evidence(self, element: dict[str, Any]) -> list[str]:
        """Extract evidence codes from an element."""
        return ExtractorUtils.extract_evidence(element)

    def _extract_original(self, location: dict[str, Any]) -> str | None:
        """Extract original sequence from location."""
        # Try finding sequence in nested location
        if position := location.get("position"):
            # Not strictly correct as original is usually separate?
            # XML schema: location has sequence? No, usually distinct.
            # But sometimes in variation.
            pass
        return None  # Placeholder, needs clearer mapping if available in XML

    def _extract_variation(self, location: dict[str, Any]) -> list[str]:
        """Extract sequence variations."""
        # Typically variations are stored in specific fields, not location directly.
        # But for this schema mapping, we return empty if not found.
        return []

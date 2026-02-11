"""
Feature extractor for UniProt JSON data.
"""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.domain.serialization import serialize_to_json


class FeatureExtractor(AbstractExtractor):
    """
    Extracts feature information from UniProt JSON data.
    """

    def extract(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract features from a UniProt entry.

        Args:
            entry: The UniProt entry dictionary

        Returns:
            List of feature dictionaries
        """
        return []

    @staticmethod
    def _process_feature(feat: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single feature entry."""
        if not isinstance(feat, dict):
            return None

        # Get location data
        location = feat.get("location", {})

        # Extract positions
        start = None
        end = None

        if loc_start := location.get("start"):
            if val := loc_start.get("value"):
                start = val

        if loc_end := location.get("end"):
            if val := loc_end.get("value"):
                end = val

        # Build feature dictionary
        feature_dict = {
            "type": feat.get("type"),
            "description": ExtractorUtils.clean_text(feat.get("description")),
            "status": feat.get("status"),
            "id": feat.get("featureId"),
            "start": start,
            "end": end,
            "evidence": feat.get("evidences"),
        }

        # Filter out None values to match test expectations (missing keys instead of null)
        return {k: v for k, v in feature_dict.items() if v is not None}

    @staticmethod
    def extract_features(features: Any) -> str | None:
        """Extract all features as JSON string."""
        if not features or not isinstance(features, list):
            return None

        processed_features = []
        for feat in features:
            if p := FeatureExtractor._process_feature(feat):
                processed_features.append(p)

        return serialize_to_json(processed_features, ensure_ascii=False) if processed_features else None

    @staticmethod
    def extract_features_by_type(features: Any, feature_type: str) -> str | None:
        """Extract features of a specific type."""
        if not features or not isinstance(features, list):
            return None

        processed_features = []
        for feat in features:
            if isinstance(feat, dict) and feat.get("type") == feature_type:
                if p := FeatureExtractor._process_feature(feat):
                    processed_features.append(p)

        return serialize_to_json(processed_features, ensure_ascii=False) if processed_features else None

    # Specific extractors delegates
    @staticmethod
    def extract_domains(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Domain")

    @staticmethod
    def extract_binding_sites(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Binding site")

    @staticmethod
    def extract_active_sites(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Active site")

    @staticmethod
    def extract_topology(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Topological domain")

    @staticmethod
    def extract_transmembrane(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Transmembrane")

    @staticmethod
    def extract_intramembrane(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Intramembrane")

    @staticmethod
    def extract_signal_peptide(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Signal peptide")

    @staticmethod
    def extract_propeptide(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Propeptide")

    @staticmethod
    def extract_glycosylation(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Glycosylation")

    @staticmethod
    def extract_lipidation(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Lipidation")

    @staticmethod
    def extract_disulfide_bonds(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Disulfide bond")

    @staticmethod
    def extract_modified_residues(features: Any) -> str | None:
        return FeatureExtractor.extract_features_by_type(features, "Modified residue")

    @staticmethod
    def extract_phosphorylation(features: Any) -> str | None:
        if not features or not isinstance(features, list): return None

        results = []
        for feat in features:
            if isinstance(feat, dict) and feat.get("type") == "Modified residue":
                desc = feat.get("description", "")
                if "phospho" in desc.lower():
                    if p := FeatureExtractor._process_feature(feat):
                        results.append(p)
        return serialize_to_json(results, ensure_ascii=False) if results else None

    @staticmethod
    def extract_acetylation(features: Any) -> str | None:
        if not features or not isinstance(features, list): return None

        results = []
        for feat in features:
            if isinstance(feat, dict) and feat.get("type") == "Modified residue":
                desc = feat.get("description", "")
                if "acetyl" in desc.lower():
                    if p := FeatureExtractor._process_feature(feat):
                        results.append(p)
        return serialize_to_json(results, ensure_ascii=False) if results else None

    @staticmethod
    def extract_ubiquitination(features: Any) -> str | None:
        if not features or not isinstance(features, list): return None

        results = []
        for feat in features:
            if isinstance(feat, dict):
                t = feat.get("type")
                desc = feat.get("description", "")
                if t in ("Cross-link", "Modified residue") and "ubiquitin" in desc.lower():
                    if p := FeatureExtractor._process_feature(feat):
                        results.append(p)
        return serialize_to_json(results, ensure_ascii=False) if results else None

    @staticmethod
    def extract_keywords(keywords: Any) -> str | None:
        """Extract keywords."""
        if not keywords or not isinstance(keywords, list):
            return None

        keyword_list = []
        for kw in keywords:
            if isinstance(kw, dict):
                # Return the whole dict to preserve ID/Name/Category structure
                keyword_list.append(kw)
            elif isinstance(kw, str):
                keyword_list.append({"name": kw}) # Normalize string to dict? Or just append?
                # If mixed, this might be messy. Assuming consistent input.

        return serialize_to_json(keyword_list, ensure_ascii=False) if keyword_list else None

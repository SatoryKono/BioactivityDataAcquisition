"""Feature and keyword extraction for UniProt records."""

from __future__ import annotations

__all__ = ["FeatureExtractor"]

from collections.abc import Iterator
from typing import ClassVar

from bioetl.application.pipelines.uniprot.extractors._feature_wrappers_mixin import (
    FeatureExtractionWrappersMixin,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


def _extract_feature_location(  # Any: JSON values
    location: JsonDict,  # Any: untyped API JSON record
    feature_data: JsonDict,  # Any: untyped API JSON record
) -> None:
    """Extract start/end positions from feature location.

    Args:
        location: Location dict from feature.
        feature_data: Feature dict to add positions to.
    """
    start = location.get("start", {})
    end = location.get("end", {})
    if isinstance(start, dict) and start.get("value"):
        feature_data["start"] = start.get("value")
    if isinstance(end, dict) and end.get("value"):
        feature_data["end"] = end.get("value")


def _iter_matching_modified_residues(
    features: list[JsonDict],  # Any: untyped API JSON records
    target_type: str,
    normalized_patterns: tuple[str, ...],
) -> Iterator[JsonDict]:  # Any: JSON values
    """Yield modified residue features whose description matches any pattern."""
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != target_type:
            continue
        description = feature.get("description")
        if not description or not isinstance(description, str):
            continue
        if any(pattern in description.lower() for pattern in normalized_patterns):
            feature_data = _build_feature_dict(feature)
            if feature_data:
                yield feature_data


def _build_feature_dict(feature: JsonDict) -> JsonDict:  # Any: JSON values
    """Build a feature data dictionary.

    Args:
        feature: Raw feature dict from API.

    Returns:
        Extracted feature data dict.
    """
    feature_data: JsonDict = {}  # Any: JSON values
    if val := feature.get("type"):
        feature_data["type"] = val
    if val := feature.get("description"):
        feature_data["description"] = val
    if val := feature.get("featureId"):
        feature_data["feature_id"] = val

    location = feature.get("location")
    if isinstance(location, dict):
        _extract_feature_location(location, feature_data)

    return feature_data


def _build_keyword_dict(kw: JsonDict) -> JsonDict:  # Any: JSON values
    """Build a keyword data dictionary.

    Args:
        kw: Raw keyword dict from API.

    Returns:
        Extracted keyword data dict.
    """
    kw_data: JsonDict = {}  # Any: JSON values
    if kw.get("id"):
        kw_data["id"] = kw.get("id")
    if kw.get("name"):
        kw_data["name"] = kw.get("name")
    if kw.get("category"):
        kw_data["category"] = kw.get("category")
    return kw_data


class FeatureExtractor(FeatureExtractionWrappersMixin):
    """Extract sequence features and keywords from UniProt records."""

    # Mapping of feature names to UniProt feature types
    FEATURE_TYPES: ClassVar[dict[str, str]] = {
        "topology": "Topological domain",
        "transmembrane": "Transmembrane",
        "intramembrane": "Intramembrane",
        "glycosylation": "Glycosylation",
        "lipidation": "Lipidation",
        "disulfide_bond": "Disulfide bond",
        "modified_residue": "Modified residue",
        "signal_peptide": "Signal peptide",
        "propeptide": "Propeptide",
    }

    # PTM patterns for filtering modified residues by description
    PTM_PATTERNS: ClassVar[dict[str, tuple[str, ...]]] = {
        "phosphorylation": ("phospho", "phosphoryl"),
        "acetylation": ("acetyl", "n-acetyl"),
        "ubiquitination": ("ubiquitin", "sumo"),
    }

    @staticmethod
    def extract_features(features: list[JsonDict] | None) -> str | None:
        """Extract all sequence features as JSON.

        Args:
            features: List of UniProt feature dicts from the API response, or None.

        Returns:
            JSON-serialized list of feature dicts (type, description, feature_id,
            start, end), or None if no features are present.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_data = _build_feature_dict(feature)
            if feature_data:
                extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_keywords(keywords: list[JsonDict] | None) -> str | None:
        """Extract UniProt keywords as JSON.

        Args:
            keywords: List of UniProt keyword dicts from the API response, or None.

        Returns:
            JSON-serialized list of keyword dicts (id, name, category),
            or None if no keywords are present.
        """
        if not keywords or not isinstance(keywords, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for kw in keywords:
            if not isinstance(kw, dict):
                continue
            kw_data = _build_keyword_dict(kw)
            if kw_data:
                extracted.append(kw_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_features_by_type(
        cls,
        features: list[JsonDict] | None,
        feature_type: str,
    ) -> str | None:
        """Extract sequence features matching the requested type.

        Args:
            features: List of UniProt feature dicts from the API response, or None.
            feature_type: UniProt feature type string to filter on
                (e.g. 'Transmembrane', 'Signal peptide').

        Returns:
            JSON-serialized list of matching feature dicts, or None if no matches.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for feature in features:
            if not isinstance(feature, dict):
                continue
            if feature.get("type") == feature_type:
                feature_data = _build_feature_dict(feature)
                if feature_data:
                    extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_ptm_by_pattern(  # Any: untyped JSON
        cls,
        features: list[JsonDict] | None,
        patterns: tuple[str, ...],
    ) -> str | None:
        """Extract modified residues whose descriptions match PTM patterns.

        Args:
            features: List of UniProt feature dicts from the API response, or None.
            patterns: Tuple of lowercase substring patterns to match against
                the modified residue description (e.g. ('phospho', 'phosphoryl')).

        Returns:
            JSON-serialized list of matching modified residue feature dicts,
            or None if no matches are found.
        """
        if not features or not isinstance(features, list) or not patterns:
            return None

        matches = list(
            _iter_matching_modified_residues(
                features,
                cls.FEATURE_TYPES["modified_residue"],
                tuple(p.lower() for p in patterns),
            )
        )
        return serialize_to_json(matches, ensure_ascii=False) if matches else None

"""Feature and keyword extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.utils import ExtractorUtils


def _extract_feature_location(
    location: dict[str, Any], feature_data: dict[str, Any]
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


def _build_feature_dict(feature: dict[str, Any]) -> dict[str, Any]:
    """Build a feature data dictionary.

    Args:
        feature: Raw feature dict from API.

    Returns:
        Extracted feature data dict.
    """
    feature_data: dict[str, Any] = {}
    if feature.get("type"):
        feature_data["type"] = feature.get("type")
    if feature.get("description"):
        feature_data["description"] = feature.get("description")
    if feature.get("featureId"):
        feature_data["feature_id"] = feature.get("featureId")

    location = feature.get("location", {})
    if isinstance(location, dict):
        _extract_feature_location(location, feature_data)

    return feature_data


def _build_keyword_dict(kw: dict[str, Any]) -> dict[str, Any]:
    """Build a keyword data dictionary.

    Args:
        kw: Raw keyword dict from API.

    Returns:
        Extracted keyword data dict.
    """
    kw_data: dict[str, Any] = {}
    if kw.get("id"):
        kw_data["id"] = kw.get("id")
    if kw.get("name"):
        kw_data["name"] = kw.get("name")
    if kw.get("category"):
        kw_data["category"] = kw.get("category")
    return kw_data


class FeatureExtractor:
    """Extracts sequence features and keywords from UniProt records."""

    @staticmethod
    def extract_features(features: Any) -> str | None:
        """Extract sequence features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of features or None.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_data = _build_feature_dict(feature)
            if feature_data:
                extracted.append(feature_data)

        return ExtractorUtils.to_json(extracted)

    @staticmethod
    def extract_keywords(keywords: Any) -> str | None:
        """Extract UniProt keywords.

        Args:
            keywords: List of keyword objects.

        Returns:
            JSON array of keywords.
        """
        if not keywords or not isinstance(keywords, list):
            return None

        extracted: list[dict[str, Any]] = []
        for kw in keywords:
            if not isinstance(kw, dict):
                continue
            kw_data = _build_keyword_dict(kw)
            if kw_data:
                extracted.append(kw_data)

        return ExtractorUtils.to_json(extracted)

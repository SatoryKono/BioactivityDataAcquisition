"""Feature and keyword extraction for UniProt records."""

from __future__ import annotations

from typing import Any, ClassVar

from bioetl.domain.serialization import serialize_to_json


def _extract_feature_location(  # Any: JSON values
    location: dict[str, Any],  # Any: untyped API JSON record
    feature_data: dict[str, Any],  # Any: untyped API JSON record
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


def _build_feature_dict(feature: dict[str, Any]) -> dict[str, Any]:  # Any: JSON values
    """Build a feature data dictionary.

    Args:
        feature: Raw feature dict from API.

    Returns:
        Extracted feature data dict.
    """
    feature_data: dict[str, Any] = {}  # Any: JSON values
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


def _build_keyword_dict(kw: dict[str, Any]) -> dict[str, Any]:  # Any: JSON values
    """Build a keyword data dictionary.

    Args:
        kw: Raw keyword dict from API.

    Returns:
        Extracted keyword data dict.
    """
    kw_data: dict[str, Any] = {}  # Any: JSON values
    if kw.get("id"):
        kw_data["id"] = kw.get("id")
    if kw.get("name"):
        kw_data["name"] = kw.get("name")
    if kw.get("category"):
        kw_data["category"] = kw.get("category")
    return kw_data


class FeatureExtractor:
    """Extracts sequence features and keywords from UniProt records."""

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
    def extract_features(features: Any) -> str | None:  # Any: untyped API JSON
        """Extract sequence features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of features or None.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[dict[str, Any]] = []  # Any: JSON values
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_data = _build_feature_dict(feature)
            if feature_data:
                extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_keywords(keywords: Any) -> str | None:  # Any: untyped API JSON
        """Extract UniProt keywords.

        Args:
            keywords: List of keyword objects.

        Returns:
            JSON array of keywords.
        """
        if not keywords or not isinstance(keywords, list):
            return None

        extracted: list[dict[str, Any]] = []  # Any: JSON values
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
        features: Any,  # Any: untyped API JSON
        feature_type: str,  # Any: untyped UniProt API JSON
    ) -> str | None:  # Any: untyped UniProt JSON
        """Extract sequence features by type.

        Args:
            features: List of feature objects.
            feature_type: Type of features to extract (e.g., "Domain", "Active site").

        Returns:
            JSON array of matching features or None.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[dict[str, Any]] = []  # Any: JSON values
        for feature in features:
            if not isinstance(feature, dict):
                continue
            if feature.get("type") == feature_type:
                feature_data = _build_feature_dict(feature)
                if feature_data:
                    extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_domains(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract protein domain features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of domain features or None.
        """
        return cls.extract_features_by_type(features, "Domain")

    @classmethod
    def extract_binding_sites(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract binding site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of binding site features or None.
        """
        return cls.extract_features_by_type(features, "Binding site")

    @classmethod
    def extract_active_sites(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract active site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of active site features or None.
        """
        return cls.extract_features_by_type(features, "Active site")

    @classmethod
    def extract_topology(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract topological domain features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of topological domain features or None.
        """
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["topology"])

    @classmethod
    def extract_transmembrane(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract transmembrane region features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of transmembrane features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["transmembrane"]
        )

    @classmethod
    def extract_intramembrane(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract intramembrane region features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of intramembrane features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["intramembrane"]
        )

    @classmethod
    def extract_glycosylation(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract glycosylation site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of glycosylation features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["glycosylation"]
        )

    @classmethod
    def extract_lipidation(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract lipidation site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of lipidation features or None.
        """
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["lipidation"])

    @classmethod
    def extract_disulfide_bonds(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract disulfide bond features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of disulfide bond features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["disulfide_bond"]
        )

    @classmethod
    def extract_modified_residues(
        cls,
        features: Any,  # Any: untyped UniProt API JSON
    ) -> str | None:  # Any: untyped UniProt JSON
        """Extract modified residue features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of modified residue features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["modified_residue"]
        )

    @classmethod
    def extract_signal_peptide(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract signal peptide features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of signal peptide features or None.
        """
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["signal_peptide"]
        )

    @classmethod
    def extract_propeptide(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract propeptide features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of propeptide features or None.
        """
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["propeptide"])

    @classmethod
    def extract_ptm_by_pattern(  # Any: untyped JSON
        cls,
        features: Any,  # Any: untyped API JSON
        patterns: tuple[str, ...],  # Any: untyped UniProt API JSON
    ) -> str | None:
        """Extract modified residue features matching PTM patterns.

        Filters modified residues by checking if description contains
        any of the given patterns (case-insensitive).

        Args:
            features: List of feature objects.
            patterns: Tuple of pattern strings to match in description.

        Returns:
            JSON array of matching modified residue features or None.
        """
        if not features or not isinstance(features, list):
            return None

        if not patterns:
            return None

        mod_res_type = cls.FEATURE_TYPES["modified_residue"]
        extracted: list[dict[str, Any]] = []  # Any: JSON values

        # Pre-normalize patterns once to avoid repeated lower() calls
        normalized_patterns = tuple(p.lower() for p in patterns)

        for feature in features:
            if not isinstance(feature, dict):
                continue
            if feature.get("type") != mod_res_type:
                continue

            description = feature.get("description")
            if not description or not isinstance(description, str):
                continue

            description_lower = description.lower()
            if any(pattern in description_lower for pattern in normalized_patterns):
                feature_data = _build_feature_dict(feature)
                if feature_data:
                    extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_phosphorylation(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract phosphorylation site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of phosphorylation features or None.
        """
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["phosphorylation"])

    @classmethod
    def extract_acetylation(cls, features: Any) -> str | None:  # Any: untyped API JSON
        """Extract acetylation site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of acetylation features or None.
        """
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["acetylation"])

    @classmethod
    def extract_ubiquitination(cls, features: Any) -> str | None:  # Any: untyped JSON
        """Extract ubiquitination site features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of ubiquitination features or None.
        """
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["ubiquitination"])

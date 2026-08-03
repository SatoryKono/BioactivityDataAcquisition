"""Wrapper mixin for typed UniProt feature extractor entry points."""

from __future__ import annotations

from typing import ClassVar, Protocol

from bioetl.domain.types import JsonDict


class _FeatureExtractorProtocol(Protocol):
    """Protocol describing core extraction methods required by wrappers."""

    FEATURE_TYPES: ClassVar[dict[str, str]]
    PTM_PATTERNS: ClassVar[dict[str, tuple[str, ...]]]

    @classmethod
    def extract_features_by_type(
        cls,
        features: list[JsonDict] | None,
        feature_type: str,
    ) -> str | None:
        """Extract features matching the given UniProt feature type."""
        ...

    @classmethod
    def extract_ptm_by_pattern(
        cls,
        features: list[JsonDict] | None,
        patterns: tuple[str, ...],
    ) -> str | None:
        """Extract post-translational modifications matching the given patterns."""
        ...


class FeatureExtractionWrappersMixin:
    """Thin wrappers mapped to specific UniProt feature/PTM groups.

    Each method delegates to ``extract_features_by_type`` or
    ``extract_ptm_by_pattern`` with the appropriate feature type key.
    """

    FEATURE_TYPES: ClassVar[dict[str, str]]
    PTM_PATTERNS: ClassVar[dict[str, tuple[str, ...]]]

    @classmethod
    def extract_domains(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract protein domain annotations."""
        return cls.extract_features_by_type(features, "Domain")

    @classmethod
    def extract_binding_sites(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract binding site annotations."""
        return cls.extract_features_by_type(features, "Binding site")

    @classmethod
    def extract_active_sites(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract active site annotations."""
        return cls.extract_features_by_type(features, "Active site")

    @classmethod
    def extract_topology(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract topological domain annotations."""
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["topology"])

    @classmethod
    def extract_transmembrane(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract transmembrane region annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["transmembrane"]
        )

    @classmethod
    def extract_intramembrane(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract intramembrane region annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["intramembrane"]
        )

    @classmethod
    def extract_glycosylation(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract glycosylation site annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["glycosylation"]
        )

    @classmethod
    def extract_lipidation(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract lipidation site annotations."""
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["lipidation"])

    @classmethod
    def extract_disulfide_bonds(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract disulfide bond annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["disulfide_bond"]
        )

    @classmethod
    def extract_modified_residues(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract modified residue annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["modified_residue"]
        )

    @classmethod
    def extract_signal_peptide(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract signal peptide annotations."""
        return cls.extract_features_by_type(
            features, cls.FEATURE_TYPES["signal_peptide"]
        )

    @classmethod
    def extract_propeptide(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract propeptide annotations."""
        return cls.extract_features_by_type(features, cls.FEATURE_TYPES["propeptide"])

    @classmethod
    def extract_phosphorylation(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract phosphorylation PTM annotations."""
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["phosphorylation"])

    @classmethod
    def extract_acetylation(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract acetylation PTM annotations."""
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["acetylation"])

    @classmethod
    def extract_ubiquitination(
        cls: type[_FeatureExtractorProtocol],
        features: list[JsonDict] | None,
    ) -> str | None:
        """Extract ubiquitination PTM annotations."""
        return cls.extract_ptm_by_pattern(features, cls.PTM_PATTERNS["ubiquitination"])

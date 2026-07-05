"""Source-specific ChEMBL publication type subset policy governance tests.

This test module enforces the separation between:
1. Global publication type taxonomy (configs/enums/chembl.yaml -> publication.types)
2. ChEMBL-specific DQ/filter subset (configs/entities/chembl/publication.yaml)

The global taxonomy must remain broad and cross-provider. ChEMBL entity config
may define a source-specific subset for its own ingestion constraints, but this
must be clearly documented as source-specific and must not redefine the global
taxonomy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.schemas.constants import PUBLICATION_TYPES
from tests.architecture._entity_contract_metadata_registry import (
    load_shared_quality_metadata,
)
from tests.architecture._entity_filter_metadata_registry import (
    load_shared_filter_metadata,
)

pytestmark = [pytest.mark.architecture]


@pytest.fixture(scope="module")
def chembl_enum_config() -> dict[str, Any]:
    """Load global ChEMBL enum config."""
    yaml_path = Path("configs/enums/chembl.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def chembl_publication_entity_config() -> dict[str, Any]:
    """Load ChEMBL publication entity config."""
    yaml_path = Path("configs/entities/chembl/publication.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def _chembl_enum_config(chembl_enum_config: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible alias for tests that still request the private name."""
    return chembl_enum_config


@pytest.fixture(scope="module")
def _chembl_publication_entity_config(
    chembl_publication_entity_config: dict[str, Any],
) -> dict[str, Any]:
    """Backward-compatible alias for tests that still request the private name."""
    return chembl_publication_entity_config


class TestGlobalPublicationTaxonomy:
    """Global publication type taxonomy must remain broad and cross-provider."""

    def test_global_publication_taxonomy_is_broad(
        self, chembl_enum_config: dict[str, Any]
    ) -> None:
        """Global publication.types must include all cross-provider types."""
        global_types = frozenset(chembl_enum_config["publication"]["types"])

        # Verify the global taxonomy includes the 19 expected types
        expected_min_count = 19
        assert len(global_types) >= expected_min_count, (
            f"Global publication taxonomy must include at least {expected_min_count} "
            f"cross-provider types, found {len(global_types)}"
        )

        # Verify it includes types beyond ChEMBL's native subset
        chembl_native_subset = {"journal-article", "book", "dataset", "patent"}
        additional_types = global_types - chembl_native_subset
        assert len(additional_types) > 0, (
            "Global publication taxonomy must include types beyond ChEMBL's "
            f"native subset {sorted(chembl_native_subset)}"
        )

        # Verify it includes known cross-provider types
        expected_cross_provider_types = {
            "review",
            "preprint",
            "letter",
            "editorial",
            "clinical-trial",
            "meta-analysis",
            "case-reports",
            "comparative-study",
            "evaluation-study",
            "book-chapter",
            "proceedings-article",
            "posted-content",
            "report",
            "standard",
            "dissertation",
            "other",
        }
        assert expected_cross_provider_types <= global_types, (
            "Global publication taxonomy must include expected cross-provider types"
        )

    def test_global_taxonomy_documentation_exists(
        self, _chembl_enum_config: dict[str, Any]
    ) -> None:
        """Global enum must document cross-provider scope."""
        # The YAML should have a comment section explaining global scope
        yaml_path = Path("configs/enums/chembl.yaml")
        yaml_content = yaml_path.read_text(encoding="utf-8")

        assert (
            "Canonical source of truth" in yaml_content
            or "cross-provider" in yaml_content
        ), "Global publication enum config must document cross-provider scope"

        assert (
            "provider-specific" in yaml_content
            or "individual providers" in yaml_content
            or "source-specific" in yaml_content
        ), "Global publication enum config must reference provider-specific policies"


class TestChEMBLSourceSpecificSubset:
    """ChEMBL entity config must define a source-specific subset with metadata."""

    def test_chembl_subset_is_proper_subset_of_global(
        self,
        chembl_enum_config: dict[str, Any],
        chembl_publication_entity_config: dict[str, Any],
    ) -> None:
        """ChEMBL publication_type allowed values must be a proper subset of global."""
        global_types = frozenset(chembl_enum_config["publication"]["types"])

        # Extract ChEMBL DQ allowed values
        chembl_allowed = set()
        for validation in chembl_publication_entity_config.get("quality", {}).get(
            "entity_field_validations", []
        ):
            if (
                validation.get("field") == "publication_type"
                and "allowed" in validation
            ):
                chembl_allowed.update(validation["allowed"])

        chembl_allowed_frozenset = frozenset(chembl_allowed)

        # Must be a subset
        assert chembl_allowed_frozenset <= global_types, (
            f"ChEMBL publication_type allowed values {sorted(chembl_allowed_frozenset)} "
            f"must be a subset of global types {sorted(global_types)}"
        )

        # Must be a proper subset (not equal) - ChEMBL should not redefine global taxonomy
        assert chembl_allowed_frozenset < global_types, (
            f"ChEMBL publication_type allowed values {sorted(chembl_allowed_frozenset)} "
            f"must be a proper subset (not equal) of global types {sorted(global_types)}. "
            "ChEMBL subset must not redefine the global taxonomy."
        )

        # Verify expected ChEMBL subset
        expected_chembl_subset = {"journal-article", "book", "dataset", "patent"}
        assert chembl_allowed_frozenset == expected_chembl_subset, (
            f"ChEMBL publication_type allowed values should be {sorted(expected_chembl_subset)}"
        )

    def test_chembl_subset_metadata_exists(
        self,
        chembl_publication_entity_config: dict[str, Any],
    ) -> None:
        """ChEMBL entity config must have metadata documenting source-specific policy."""
        quality_metadata = load_shared_quality_metadata(
            "configs/entities/chembl/publication.yaml"
        )

        assert "publication_type_policy" in quality_metadata, (
            "ChEMBL publication entity config must have quality.metadata.publication_type_policy"
        )

        policy = quality_metadata["publication_type_policy"]
        assert policy.get("scope") == "source_specific", (
            "publication_type_policy must be marked as source_specific"
        )

        assert "description" in policy, (
            "publication_type_policy must have a description"
        )

        description = policy["description"]
        assert (
            "SOURCE-SPECIFIC" in description or "source specific" in description.lower()
        ), (
            "publication_type_policy description must explicitly state this is source-specific"
        )

        assert "global" in description.lower(), (
            "publication_type_policy description must reference the global taxonomy"
        )

        assert "configs/enums/chembl.yaml" in description, (
            "publication_type_policy must reference the global enum config path"
        )

    def test_chembl_filter_policy_metadata_exists(
        self,
    ) -> None:
        """ChEMBL filter config must have metadata documenting source-specific policy."""
        filters_metadata = load_shared_filter_metadata(
            "configs/entities/chembl/publication.yaml"
        )

        assert "publication_filter_policy" in filters_metadata, (
            "ChEMBL publication entity config must have filters.metadata.publication_filter_policy"
        )

        policy = filters_metadata["publication_filter_policy"]
        assert policy.get("scope") == "source_specific", (
            "publication_filter_policy must be marked as source_specific"
        )

        assert "description" in policy, (
            "publication_filter_policy must have a description"
        )

        description = policy["description"]
        assert (
            "SOURCE-SPECIFIC" in description or "source specific" in description.lower()
        ), (
            "publication_filter_policy description must explicitly state this is source-specific"
        )

    def test_field_semantics_documentation_exists(
        self,
        chembl_publication_entity_config: dict[str, Any],
    ) -> None:
        """ChEMBL entity config must document publication_type_raw vs publication_type semantics."""
        quality_metadata = load_shared_quality_metadata(
            "configs/entities/chembl/publication.yaml"
        )
        policy = quality_metadata.get("publication_type_policy", {})

        assert "field_semantics" in policy, (
            "publication_type_policy must document field semantics"
        )

        field_semantics = policy["field_semantics"]
        assert "publication_type_raw" in field_semantics, (
            "field_semantics must document publication_type_raw"
        )

        assert "publication_type" in field_semantics, (
            "field_semantics must document publication_type"
        )

        # Verify publication_type_raw description mentions preservation
        raw_desc = field_semantics["publication_type_raw"]
        assert any(
            term in raw_desc.lower() for term in ["raw", "native", "preserve"]
        ), (
            "publication_type_raw description must mention preservation of raw/native values"
        )

        # Verify publication_type description mentions canonical/global taxonomy
        canonical_desc = field_semantics["publication_type"]
        assert any(
            term in canonical_desc.lower()
            for term in ["canonical", "global", "taxonomy"]
        ), "publication_type description must mention canonical/global taxonomy"


class TestPythonConstantsSync:
    """Python constants must match global enum, not ChEMBL subset."""

    def test_python_publication_types_match_global_enum(
        self,
        chembl_enum_config: dict[str, Any],
    ) -> None:
        """Python PUBLICATION_TYPES must match global enum, not ChEMBL subset."""
        global_types = frozenset(chembl_enum_config["publication"]["types"])

        assert PUBLICATION_TYPES == global_types, (
            "Python PUBLICATION_TYPES constant must match global publication.types "
            "from configs/enums/chembl.yaml, not the ChEMBL-specific subset"
        )

        # Verify it's the broad taxonomy, not the ChEMBL subset
        chembl_subset = {"journal-article", "book", "dataset", "patent"}
        assert PUBLICATION_TYPES != frozenset(chembl_subset), (
            "Python PUBLICATION_TYPES must be the broad global taxonomy, "
            "not the ChEMBL-specific subset"
        )


class TestFilterSubsetGovernance:
    """Silver/gold filters must be documented as source-specific constraints."""

    def test_silver_filter_does_not_carry_publication_type_subset(
        self,
        chembl_publication_entity_config: dict[str, Any],
    ) -> None:
        """Publication type is semantic Gold/source-profile policy, not Silver."""
        silver_filters = chembl_publication_entity_config.get("filters", {}).get(
            "silver_filters", {}
        )

        assert "columns" not in silver_filters
        assert "ranges" not in silver_filters

    def test_gold_filter_is_subset_of_global(
        self,
        chembl_enum_config: dict[str, Any],
        chembl_publication_entity_config: dict[str, Any],
    ) -> None:
        """Gold filter must be a subset of global taxonomy."""
        global_types = frozenset(chembl_enum_config["publication"]["types"])

        gold_filters = chembl_publication_entity_config.get("filters", {}).get(
            "gold_filters", {}
        )
        gold_types = frozenset(
            gold_filters.get("columns", {}).get("publication_type", [])
        )

        if gold_types:
            assert gold_types <= global_types, (
                f"Gold filter types {sorted(gold_types)} must be a subset of "
                f"global types {sorted(global_types)}"
            )

    def test_filter_comments_document_source_specific_scope(
        self,
    ) -> None:
        """Shared filter policy registry must document source-specific scope."""
        policy = load_shared_filter_metadata(
            "configs/entities/chembl/publication.yaml"
        )["publication_filter_policy"]
        description = str(policy.get("description", ""))

        assert "source-specific" in description.lower(), (
            "Publication filter policy must document source-specific scope"
        )
        assert "global" in description.lower(), (
            "Publication filter policy must explicitly reference the global taxonomy boundary"
        )

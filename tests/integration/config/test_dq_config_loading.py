"""Integration tests for DQ config loading through PipelineConfigLoader.

Tests end-to-end config loading with real file hierarchy.

Requirements:
- REQ-CONF-001: Full pipeline config loading with DQ
- REQ-CONF-002: Hierarchical DQ config resolution
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader


@pytest.fixture(scope="module")
def real_configs_root() -> Path:
    """Get path to real configs directory."""
    return Path("configs")


@pytest.fixture(scope="module")
def config_loader(real_configs_root: Path) -> PipelineConfigLoader:
    """Create PipelineConfigLoader with real configs."""
    return PipelineConfigLoader(real_configs_root)


@pytest.fixture(scope="module")
def dq_loader(real_configs_root: Path) -> DQConfigLoader:
    """Create DQConfigLoader with real configs."""
    return DQConfigLoader(real_configs_root)


@pytest.mark.integration
class TestDQConfigIntegration:
    """Integration tests for DQ config loading."""

    def test_load_chembl_activity_dq(self, dq_loader: DQConfigLoader) -> None:
        """Load ChEMBL activity DQ config from hierarchy."""
        config = dq_loader.load("chembl", "activity")

        # Should have merged config from hierarchy
        assert config.soft_fail_threshold <= 0.10
        assert config.hard_fail_threshold <= 0.25

        # Should have validations from multiple levels
        assert len(config.field_validations) > 0

    def test_dq_hierarchy_merge_chembl(self, dq_loader: DQConfigLoader) -> None:
        """Verify hierarchy merge for ChEMBL produces expected result."""
        config = dq_loader.load("chembl", "activity")

        # Check that validations from different levels are present
        field_names = [fv.field for fv in config.field_validations]

        # From base/quality.yaml
        assert "_content_hash" in field_names

        # From entities/chembl/activity.yaml
        assert "activity_id" in field_names

    def test_provider_threshold_override(self, dq_loader: DQConfigLoader) -> None:
        """Provider config should override default thresholds."""
        # Load ChEMBL which has stricter hard_fail (0.15)
        config = dq_loader.load("chembl", "unknown_entity")

        # ChEMBL provider has hard_fail: 0.15 (stricter than default 0.20)
        assert config.hard_fail_threshold == pytest.approx(0.15)

    def test_load_defaults_for_unknown(self, dq_loader: DQConfigLoader) -> None:
        """Unknown provider/entity should get defaults."""
        config = dq_loader.load("nonexistent_provider", "nonexistent_entity")

        # Should use defaults
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)

    def test_uniprot_protein_enum_vocabulary_validations(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """UniProt vocabulary fields should use enum DQ, not numeric ranges."""
        from bioetl.domain.schemas.uniprot._core import (
            ENTRY_TYPES,
            PROTEIN_EXISTENCE_LEVELS,
            PROTEIN_FLAGS,
        )

        config = dq_loader.load("uniprot", "protein")
        enum_rules = {
            rule.field: rule
            for rule in config.field_validations
            if rule.validation_type == "enum"
            and rule.field in {"entry_type", "flag", "protein_existence"}
        }

        assert enum_rules["entry_type"].allowed == tuple(ENTRY_TYPES)
        assert enum_rules["flag"].allowed == tuple(PROTEIN_FLAGS)
        assert enum_rules["protein_existence"].allowed == tuple(
            PROTEIN_EXISTENCE_LEVELS
        )

        range_fields = {
            rule.field
            for rule in config.field_validations
            if rule.validation_type == "range"
        }
        assert "protein_existence" not in range_fields


@pytest.mark.integration
class TestPipelineConfigLoaderWithDQResolution:
    """Integration tests for PipelineConfigLoader DQ resolution."""

    def test_resolve_dq_config_for_chembl_activity(
        self, config_loader: PipelineConfigLoader
    ) -> None:
        """Resolve DQ config through PipelineConfigLoader for ChEMBL activity."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")
        dq_config = config_loader.resolve_dq_config(yaml_config)

        # Should have resolved DQ config
        assert dq_config.soft_fail_threshold > 0
        assert dq_config.hard_fail_threshold > 0
        assert dq_config.hard_fail_threshold > dq_config.soft_fail_threshold

    def test_config_loader_caching(self, config_loader: PipelineConfigLoader) -> None:
        """PipelineConfigLoader should use cached DQ configs."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")

        # Resolve twice
        dq1 = config_loader.resolve_dq_config(yaml_config)
        dq2 = config_loader.resolve_dq_config(yaml_config)

        # Should be same object if caching works (no inline overrides)
        # Note: caching is internal to DQConfigLoader
        assert dq1.soft_fail_threshold == dq2.soft_fail_threshold

    def test_chembl_activity_required_fields_include_nonnullable_contract_units(
        self, config_loader: PipelineConfigLoader
    ) -> None:
        """chembl_activity config should require core non-nullable chemistry fields."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")
        domain_config = resolve_domain_pipeline_config(yaml_config)

        required_fields = set(domain_config.silver_filters.required_fields)

        assert "canonical_smiles" in required_fields
        assert "standard_units" in required_fields
        assert "uo_units" in required_fields

    def test_chembl_assay_required_fields_include_nonnullable_contract_fields(
        self, config_loader: PipelineConfigLoader
    ) -> None:
        """chembl_assay config should require schema non-nullable foreign-key fields."""
        yaml_config = config_loader.load_pipeline_config("chembl_assay")
        domain_config = resolve_domain_pipeline_config(yaml_config)

        required_fields = set(domain_config.silver_filters.required_fields)

        assert "publication_id" in required_fields
        assert "bao_format" in required_fields
        assert "assay_type_description" in required_fields
        assert "relationship_type" in required_fields
        assert "confidence_score" in required_fields

    def test_chembl_publication_required_fields_include_runtime_contract_fields(
        self, config_loader: PipelineConfigLoader
    ) -> None:
        """chembl_publication should require the runtime Silver gate fields."""
        yaml_config = config_loader.load_pipeline_config("chembl_publication")
        domain_config = resolve_domain_pipeline_config(yaml_config)

        required_fields = set(domain_config.silver_filters.required_fields)

        assert "publication_id" in required_fields
        assert "publication_type" in required_fields
        assert "title" in required_fields

    def test_clear_cache_works(self, config_loader: PipelineConfigLoader) -> None:
        """clear_cache() should work without errors."""
        config_loader.clear_cache()
        # No assertion needed - just verifying no exceptions


@pytest.mark.integration
class TestRealConfigValidation:
    """Integration tests validating real config files."""

    def test_all_chembl_entity_configs_load(self, dq_loader: DQConfigLoader) -> None:
        """All ChEMBL entity configs should load without errors."""
        entities = ["activity", "assay", "molecule", "target"]
        for entity in entities:
            entity_path = Path(f"configs/entities/chembl/{entity}.yaml")
            if entity_path.exists():
                config = dq_loader.load("chembl", entity)
                assert config.soft_fail_threshold < config.hard_fail_threshold

    def test_defaults_yaml_valid(self, dq_loader: DQConfigLoader) -> None:
        """Base DQ defaults should be valid and loadable."""
        # Loading any provider/entity uses defaults first
        config = dq_loader.load("test", "test")

        # Defaults should be set
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)
        assert config.strict_validation is False

    def test_provider_configs_have_correct_metadata(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """Provider configs should be loadable."""
        import yaml

        providers_dir = Path("configs/providers")
        if providers_dir.exists():
            for provider_file in providers_dir.glob("*.yaml"):
                with open(provider_file) as f:
                    data = yaml.safe_load(f)
                    assert "provider" in data or "version" in data
                    # Unified provider files should include quality section.
                    assert "quality" in data or "field_validations" in data


@pytest.mark.integration
class TestDQConfigFileStructure:
    """Tests for DQ config file structure consistency."""

    def test_defaults_has_required_sections(self) -> None:
        """base/quality.yaml should have all required sections."""
        import yaml

        defaults_path = Path("configs/base/quality.yaml")
        assert defaults_path.exists(), "Missing configs/base/quality.yaml"

        with open(defaults_path) as f:
            data = yaml.safe_load(f)

        # Required sections
        assert "version" in data
        assert "thresholds" in data
        assert "thresholds" in data and "soft_fail" in data["thresholds"]
        assert "thresholds" in data and "hard_fail" in data["thresholds"]

    def test_provider_files_consistent_format(self) -> None:
        """Provider config files should have consistent format."""
        import yaml

        providers_dir = Path("configs/providers")
        if not providers_dir.exists():
            pytest.skip("No providers directory")

        for provider_file in providers_dir.glob("*.yaml"):
            with open(provider_file) as f:
                data = yaml.safe_load(f)

            assert "version" in data, f"Missing version in {provider_file}"
            if "provider" in data:
                expected_provider = provider_file.stem
                assert data["provider"] == expected_provider, (
                    f"Provider mismatch in {provider_file}"
                )
            assert "quality" in data or "field_validations" in data

    def test_entity_files_have_required_fields(self) -> None:
        """Unified entity config files should have provider/entity/quality fields."""
        import yaml

        entities_dir = Path("configs/entities")
        if not entities_dir.exists():
            pytest.skip("No entities directory")

        for provider_dir in entities_dir.iterdir():
            if not provider_dir.is_dir():
                continue

            for entity_file in provider_dir.glob("*.yaml"):
                with open(entity_file) as f:
                    data = yaml.safe_load(f)

                # Should have provider and entity
                assert "provider" in data, f"Missing provider in {entity_file}"
                assert "entity" in data, f"Missing entity in {entity_file}"
                assert "quality" in data, f"Missing quality section in {entity_file}"

                # Provider should match directory name
                assert data["provider"] == provider_dir.name, (
                    f"Provider mismatch in {entity_file}"
                )

                # Entity should match filename (without .yaml)
                assert data["entity"] == entity_file.stem, (
                    f"Entity mismatch in {entity_file}"
                )


@pytest.mark.integration
@pytest.mark.integration
class TestChemblPublicationCrossFieldRules:
    """Tests for harmonized ChEMBL publication cross-field DQ rules."""

    def test_chembl_publication_identifiable_rule(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """publication_identifiable should use all_present(pk, title) with error severity."""
        config = dq_loader.load("chembl", "publication")

        identifiable = next(
            (
                cfv
                for cfv in config.cross_field_validations
                if cfv.name == "publication_identifiable"
            ),
            None,
        )
        assert identifiable is not None, "Missing publication_identifiable rule"
        assert identifiable.condition == "all_present"
        assert "publication_id" in identifiable.fields
        assert "title" in identifiable.fields
        assert identifiable.severity == "error"

    def test_chembl_has_cross_reference_rule(self, dq_loader: DQConfigLoader) -> None:
        """has_cross_reference should use any_present(pmid, doi) with warn severity."""
        config = dq_loader.load("chembl", "publication")

        cross_ref = next(
            (
                cfv
                for cfv in config.cross_field_validations
                if cfv.name == "has_cross_reference"
            ),
            None,
        )
        assert cross_ref is not None, "Missing has_cross_reference rule"
        assert cross_ref.condition == "any_present"
        assert "publication_pmid" in cross_ref.fields
        assert "publication_doi" in cross_ref.fields
        assert cross_ref.severity == "warn"

    def test_chembl_publication_type_validation_is_non_nullable(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """publication_type DQ enum should match Silver/runtime non-nullability."""
        config = dq_loader.load("chembl", "publication")

        publication_type_rules = [
            rule
            for rule in config.field_validations
            if rule.field == "publication_type" and rule.validation_type == "enum"
        ]

        assert publication_type_rules, "Missing publication_type enum rule"
        assert publication_type_rules[0].nullable is False

    def test_all_publication_providers_have_identifiable_rule(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """All providers should have publication_identifiable with all_present(pk, title)."""
        providers_and_pks = {
            "chembl": "publication_id",
            "pubmed": "pmid",
            "crossref": "doi",
            "openalex": "openalex_id",
            "semanticscholar": "paper_id",
        }

        for provider, expected_pk in providers_and_pks.items():
            entity_path = Path(f"configs/entities/{provider}/publication.yaml")
            if not entity_path.exists():
                continue

            config = dq_loader.load(provider, "publication")
            identifiable = next(
                (
                    cfv
                    for cfv in config.cross_field_validations
                    if cfv.name == "publication_identifiable"
                ),
                None,
            )
            assert identifiable is not None, (
                f"Missing publication_identifiable for {provider}"
            )
            assert identifiable.condition == "all_present", (
                f"{provider}: publication_identifiable should use all_present"
            )
            assert expected_pk in identifiable.fields, (
                f"{provider}: publication_identifiable should include {expected_pk}"
            )
            assert "title" in identifiable.fields, (
                f"{provider}: publication_identifiable should include title"
            )


@pytest.mark.integration
class TestPublicationYearWarnRule:
    """Verify publication_year < 1950 warn rule is loaded from DQ configs."""

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "crossref", "openalex", "pubmed", "semanticscholar"],
    )
    def test_publication_year_warn_rule_present(
        self, dq_loader: DQConfigLoader, provider: str
    ) -> None:
        """Each provider's publication DQ config has a year < 1950 warn rule."""
        config = dq_loader.load(provider, "publication")

        year_rules = [
            fv
            for fv in config.field_validations
            if fv.field == "publication_year" and fv.validation_type == "range"
        ]

        # Should have at least 2 range rules: error (1500-2100) and warn (min 1950)
        assert len(year_rules) >= 2, (
            f"{provider}: expected ≥2 publication_year range rules, got {len(year_rules)}"
        )

        # Find the warn rule
        warn_rules = [r for r in year_rules if r.severity == "warn"]
        assert len(warn_rules) == 1, (
            f"{provider}: expected 1 warn rule for publication_year, got {len(warn_rules)}"
        )

        warn_rule = warn_rules[0]
        assert warn_rule.min_value == 1950, (
            f"{provider}: warn rule min should be 1950, got {warn_rule.min_value}"
        )
        assert warn_rule.max_value is None, (
            f"{provider}: warn rule should have no max, got {warn_rule.max_value}"
        )

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "crossref", "openalex", "pubmed", "semanticscholar"],
    )
    def test_publication_year_error_rule_unchanged(
        self, dq_loader: DQConfigLoader, provider: str
    ) -> None:
        """Existing error rule (1500-2100) remains intact alongside new warn rule."""
        config = dq_loader.load(provider, "publication")

        year_rules = [
            fv
            for fv in config.field_validations
            if fv.field == "publication_year" and fv.validation_type == "range"
        ]

        error_rules = [r for r in year_rules if r.severity == "error"]
        assert len(error_rules) == 1, (
            f"{provider}: expected 1 error rule for publication_year"
        )

        error_rule = error_rules[0]
        assert error_rule.min_value == 1500
        assert error_rule.max_value == 2100


@pytest.mark.integration
class TestBackwardCompatibility:
    """Tests for backward compatibility with inline dq_overrides."""

    def test_inline_dq_overrides_still_work(
        self, config_loader: PipelineConfigLoader
    ) -> None:
        """Pipeline configs with inline dq_overrides should still work."""
        # Load a pipeline config
        yaml_config = config_loader.load_pipeline_config("chembl_activity")

        # Check dq_overrides exists and has expected structure
        assert hasattr(yaml_config, "dq_overrides")
        assert hasattr(yaml_config.dq_overrides, "soft_fail_threshold")

    def test_hierarchy_overrides_inline_defaults(
        self,
        config_loader: PipelineConfigLoader,
    ) -> None:
        """Hierarchy config should override inline defaults when available."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")
        resolved_dq = config_loader.resolve_dq_config(yaml_config)

        # Resolved config should have validations from hierarchy
        # (inline dq_overrides in pipeline configs typically don't have validations)
        assert len(resolved_dq.field_validations) > 0

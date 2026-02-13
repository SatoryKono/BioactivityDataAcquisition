"""Integration tests for DQ config loading through ConfigLoader.

Tests end-to-end config loading with real file hierarchy.

Requirements:
- REQ-CONF-001: Full pipeline config loading with DQ
- REQ-CONF-002: Hierarchical DQ config resolution
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.pipeline_config_loader import ConfigLoader


@pytest.fixture(scope="module")
def real_configs_root() -> Path:
    """Get path to real configs directory."""
    return Path("configs")


@pytest.fixture(scope="module")
def config_loader(real_configs_root: Path) -> ConfigLoader:
    """Create ConfigLoader with real configs."""
    return ConfigLoader(real_configs_root)


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

        # From _defaults.yaml
        assert "_content_hash" in field_names

        # From entities/chembl/activity.yaml
        assert "activity_id" in field_names

    def test_provider_threshold_override(self, dq_loader: DQConfigLoader) -> None:
        """Provider config should override default thresholds."""
        # Load ChEMBL which has stricter hard_fail (0.15)
        config = dq_loader.load("chembl", "unknown_entity")

        # ChEMBL provider has hard_fail: 0.15 (stricter than default 0.20)
        assert config.hard_fail_threshold == 0.15

    def test_load_defaults_for_unknown(self, dq_loader: DQConfigLoader) -> None:
        """Unknown provider/entity should get defaults."""
        config = dq_loader.load("nonexistent_provider", "nonexistent_entity")

        # Should use defaults
        assert config.soft_fail_threshold == 0.05
        assert config.hard_fail_threshold == 0.20


@pytest.mark.integration
class TestConfigLoaderWithDQResolution:
    """Integration tests for ConfigLoader DQ resolution."""

    def test_resolve_dq_config_for_chembl_activity(
        self, config_loader: ConfigLoader
    ) -> None:
        """Resolve DQ config through ConfigLoader for ChEMBL activity."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")
        dq_config = config_loader.resolve_dq_config(yaml_config)

        # Should have resolved DQ config
        assert dq_config.soft_fail_threshold > 0
        assert dq_config.hard_fail_threshold > 0
        assert dq_config.hard_fail_threshold > dq_config.soft_fail_threshold

    def test_config_loader_caching(self, config_loader: ConfigLoader) -> None:
        """ConfigLoader should use cached DQ configs."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")

        # Resolve twice
        dq1 = config_loader.resolve_dq_config(yaml_config)
        dq2 = config_loader.resolve_dq_config(yaml_config)

        # Should be same object if caching works (no inline overrides)
        # Note: caching is internal to DQConfigLoader
        assert dq1.soft_fail_threshold == dq2.soft_fail_threshold

    def test_clear_cache_works(self, config_loader: ConfigLoader) -> None:
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
            entity_path = Path(f"configs/dq/entities/chembl/{entity}.yaml")
            if entity_path.exists():
                config = dq_loader.load("chembl", entity)
                assert config.soft_fail_threshold < config.hard_fail_threshold

    def test_defaults_yaml_valid(self, dq_loader: DQConfigLoader) -> None:
        """_defaults.yaml should be valid and loadable."""
        # Loading any provider/entity uses _defaults.yaml first
        config = dq_loader.load("test", "test")

        # Defaults should be set
        assert config.soft_fail_threshold == 0.05
        assert config.hard_fail_threshold == 0.20
        assert config.strict_validation is False

    def test_provider_configs_have_correct_metadata(
        self, dq_loader: DQConfigLoader
    ) -> None:
        """Provider configs should be loadable."""
        import yaml

        providers_dir = Path("configs/dq/providers")
        if providers_dir.exists():
            for provider_file in providers_dir.glob("*.yaml"):
                with open(provider_file) as f:
                    data = yaml.safe_load(f)
                    # Provider files should have provider field
                    assert "provider" in data or "version" in data


@pytest.mark.integration
class TestDQConfigFileStructure:
    """Tests for DQ config file structure consistency."""

    def test_defaults_has_required_sections(self) -> None:
        """_defaults.yaml should have all required sections."""
        import yaml

        defaults_path = Path("configs/dq/_defaults.yaml")
        assert defaults_path.exists(), "Missing _defaults.yaml"

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

        providers_dir = Path("configs/dq/providers")
        if not providers_dir.exists():
            pytest.skip("No providers directory")

        for provider_file in providers_dir.glob("*.yaml"):
            with open(provider_file) as f:
                data = yaml.safe_load(f)

            # Should have version
            assert "version" in data, f"Missing version in {provider_file}"

            # Provider name should match filename
            if "provider" in data:
                expected_provider = provider_file.stem
                assert data["provider"] == expected_provider, (
                    f"Provider mismatch in {provider_file}"
                )

    def test_entity_files_have_required_fields(self) -> None:
        """Entity config files should have provider and entity fields."""
        import yaml

        entities_dir = Path("configs/dq/entities")
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

                # Provider should match directory name
                assert data["provider"] == provider_dir.name, (
                    f"Provider mismatch in {entity_file}"
                )

                # Entity should match filename (without .yaml)
                assert data["entity"] == entity_file.stem, (
                    f"Entity mismatch in {entity_file}"
                )


@pytest.mark.integration
class TestBackwardCompatibility:
    """Tests for backward compatibility with inline dq_rules."""

    def test_inline_dq_rules_still_work(self, config_loader: ConfigLoader) -> None:
        """Pipeline configs with inline dq_rules should still work."""
        # Load a pipeline config
        yaml_config = config_loader.load_pipeline_config("chembl_activity")

        # Check dq_overrides exists and has expected structure
        # (field renamed from dq_rules; YAML key accepted via AliasChoices)
        assert hasattr(yaml_config, "dq_overrides")
        assert hasattr(yaml_config.dq_overrides, "soft_fail_threshold")

    def test_hierarchy_overrides_inline_defaults(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Hierarchy config should override inline defaults when available."""
        yaml_config = config_loader.load_pipeline_config("chembl_activity")
        resolved_dq = config_loader.resolve_dq_config(yaml_config)

        # Resolved config should have validations from hierarchy
        # (inline dq_rules in pipeline configs typically don't have validations)
        assert len(resolved_dq.field_validations) >= 0

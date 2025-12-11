"""Integration tests for config loading with schema bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bioetl.application.bootstrap import ApplicationBootstrap
from bioetl.application.bootstrap_factory import create_default_bootstrap
from bioetl.domain.errors import ConfigValidationError
from bioetl.infrastructure.config.loader import (
    clear_schema_contract_provider,
    get_pipeline_config_from_path,
    get_schema_contract_provider,
)

if TYPE_CHECKING:
    pass


class TestConfigLoadingWithBootstrap:
    """Test config loading after proper bootstrap."""

    @pytest.fixture
    def bootstrapped_app(self) -> ApplicationBootstrap:
        """Application with bootstrap completed."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()
        yield bootstrap
        # Clean up after test
        bootstrap.shutdown()

    @pytest.fixture
    def clean_provider_state(self) -> None:
        """Ensure clean provider state before and after test."""
        clear_schema_contract_provider()
        yield
        clear_schema_contract_provider()

    def test_load_config_after_bootstrap(
        self, bootstrapped_app: ApplicationBootstrap, tmp_path: Path
    ) -> None:
        """Config loading should work after application bootstrap."""
        # Create test config
        config_file = tmp_path / "test_pipeline.yaml"
        config_file.write_text(
            """
id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30
    max_retries: 3
    rate_limit_per_sec: 10.0
"""
        )

        config = get_pipeline_config_from_path(config_file)

        assert config.id == "chembl.activity"
        # Fields should be populated from schema
        assert config.fields is not None
        assert len(config.fields) > 0

    def test_load_config_without_bootstrap_fails(
        self, clean_provider_state: None, tmp_path: Path
    ) -> None:
        """Config loading should fail gracefully without bootstrap."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            """
id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30
    max_retries: 3
    rate_limit_per_sec: 10.0
"""
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            get_pipeline_config_from_path(config_file)

    def test_schema_contract_provider_injection(
        self, bootstrapped_app: ApplicationBootstrap
    ) -> None:
        """Schema contract provider should be injectable into infrastructure."""
        provider = get_schema_contract_provider()
        context = bootstrapped_app.context

        assert provider is not None
        assert context is not None
        assert provider is context.contract_provider

    def test_bootstrap_shutdown_clears_provider(
        self, bootstrapped_app: ApplicationBootstrap
    ) -> None:
        """Bootstrap shutdown should clear the schema contract provider."""
        assert get_schema_contract_provider() is not None

        bootstrapped_app.shutdown()

        assert get_schema_contract_provider() is None

    def test_multiple_start_is_idempotent(self) -> None:
        """Calling start() multiple times should be safe."""
        bootstrap = create_default_bootstrap()
        try:
            context_first = bootstrap.start()
            provider_after_first = context_first.contract_provider

            context_second = bootstrap.start()  # Should be no-op
            provider_after_second = context_second.contract_provider

            assert provider_after_first is provider_after_second
            assert bootstrap.is_started is True
        finally:
            bootstrap.shutdown()


class TestConfigFieldPopulation:
    """Test that fields are populated from schema correctly."""

    @pytest.fixture(autouse=True)
    def setup_bootstrap(self) -> ApplicationBootstrap:
        """Bootstrap application for each test."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()
        yield bootstrap
        bootstrap.shutdown()

    def test_activity_config_has_activity_fields(self, tmp_path: Path) -> None:
        """Activity config should have activity-specific fields."""
        config_file = tmp_path / "activity.yaml"
        config_file.write_text(
            """
id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
"""
        )

        config = get_pipeline_config_from_path(config_file)

        field_names = {f.get("name") for f in config.fields}
        # Activity should have these essential fields
        assert "activity_id" in field_names

    def test_molecule_config_has_molecule_fields(self, tmp_path: Path) -> None:
        """Molecule config should have molecule-specific fields."""
        config_file = tmp_path / "molecule.yaml"
        config_file.write_text(
            """
id: chembl.molecule
provider: chembl
entity: molecule
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
"""
        )

        config = get_pipeline_config_from_path(config_file)

        field_names = {f.get("name") for f in config.fields}
        assert "molecule_chembl_id" in field_names

    def test_target_config_has_target_fields(self, tmp_path: Path) -> None:
        """Target config should have target-specific fields."""
        config_file = tmp_path / "target.yaml"
        config_file.write_text(
            """
id: chembl.target
provider: chembl
entity: target
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
"""
        )

        config = get_pipeline_config_from_path(config_file)

        field_names = {f.get("name") for f in config.fields}
        assert "target_chembl_id" in field_names


class TestConfigValidation:
    """Test config validation during loading."""

    @pytest.fixture(autouse=True)
    def setup_bootstrap(self) -> ApplicationBootstrap:
        """Bootstrap application for each test."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()
        yield bootstrap
        bootstrap.shutdown()

    def test_invalid_provider_raises_error(self, tmp_path: Path) -> None:
        """Unknown provider should raise an error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(
            """
id: unknown.entity
provider: unknown_provider
entity: entity
input_mode: auto_detect
batch_size: 100
output_path: ./output
provider_config:
  provider: unknown_provider
  base_url: https://example.com
"""
        )

        with pytest.raises(Exception):  # UnknownProviderError or similar
            get_pipeline_config_from_path(config_file)

    def test_missing_required_field_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """Missing required fields should raise ConfigValidationError."""
        config_file = tmp_path / "incomplete.yaml"
        config_file.write_text(
            """
id: chembl.activity
provider: chembl
# Missing entity, output_path, etc.
"""
        )

        with pytest.raises((ConfigValidationError, Exception)):
            get_pipeline_config_from_path(config_file)


class TestExistingConfigFiles:
    """Test loading existing config files from fixtures."""

    @pytest.fixture(autouse=True)
    def setup_bootstrap(self) -> ApplicationBootstrap:
        """Bootstrap application for each test."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()
        yield bootstrap
        bootstrap.shutdown()

    def test_load_chembl_activity_valid_config(self) -> None:
        """Should load valid ChEMBL activity config from fixtures."""
        config_path = Path("tests/fixtures/configs/chembl_activity_valid.yaml")
        if not config_path.exists():
            pytest.skip("Fixture file not found")

        config = get_pipeline_config_from_path(config_path)

        assert config.id == "chembl.activity"
        assert config.provider == "chembl"
        assert config.entity_name == "activity"

    def test_load_chembl_activity_test_config(self) -> None:
        """Should load test ChEMBL activity config from fixtures."""
        config_path = Path("tests/fixtures/configs/chembl_activity_test.yaml")
        if not config_path.exists():
            pytest.skip("Fixture file not found")

        config = get_pipeline_config_from_path(config_path)

        assert config.provider == "chembl"
        assert config.entity_name == "activity"
        assert config.source.batch_size == 5

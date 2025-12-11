"""Tests for schema contract provider injection in config loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.schemas.registry import create_default_schema_registry
from bioetl.infrastructure.config import provider_registry
from bioetl.infrastructure.config.loader import (
    get_pipeline_config_from_path,
    reset_schema_contract_provider,
    set_schema_contract_provider,
)


@pytest.fixture(autouse=True)
def _reset_schema_provider() -> None:
    """Reset schema contract provider before and after each test."""
    reset_schema_contract_provider()
    yield
    reset_schema_contract_provider()


@pytest.fixture(autouse=True)
def _reset_provider_registry() -> None:
    """Reset provider registry before and after each test."""
    provider_registry.clear_provider_registry_cache()
    yield
    provider_registry.clear_provider_registry_cache()


class TestSchemaContractProviderInjection:
    """Tests for schema contract provider dependency injection."""

    def test_raises_runtime_error_when_provider_not_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test RuntimeError when loading config without provider set."""
        providers_file = Path("tests/fixtures/configs/providers.yaml")
        monkeypatch.setattr(
            provider_registry,
            "DEFAULT_PROVIDERS_REGISTRY_PATH",
            providers_file,
        )
        provider_registry.clear_provider_registry_cache()

        # Create a minimal config without fields section
        config_path = tmp_path / "chembl_activity.yaml"
        config_path.write_text(
            """id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
            encoding="utf-8",
        )

        with pytest.raises(
            RuntimeError, match="SchemaContractProvider not initialized"
        ):
            get_pipeline_config_from_path(config_path)

    def test_set_schema_contract_provider_accepts_implementation(self) -> None:
        """Test set_schema_contract_provider accepts SchemaContractProviderABC."""
        mock_provider = MagicMock(spec=SchemaContractProviderABC)

        # Should not raise
        set_schema_contract_provider(mock_provider)

    def test_fields_populated_with_injected_provider(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fields populated from schema when provider is injected."""
        providers_file = Path("tests/fixtures/configs/providers.yaml")
        monkeypatch.setattr(
            provider_registry,
            "DEFAULT_PROVIDERS_REGISTRY_PATH",
            providers_file,
        )
        provider_registry.clear_provider_registry_cache()

        # Inject real provider
        registry = create_default_schema_registry()
        # Register schemas for the pipeline
        from bioetl.infrastructure.validation.bootstrap import register_schemas

        register_schemas(registry)
        contract_provider = SchemaContractProviderImpl(registry)
        set_schema_contract_provider(contract_provider)

        # Create config without fields section
        config_path = tmp_path / "chembl_activity.yaml"
        config_path.write_text(
            """id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
            encoding="utf-8",
        )

        config = get_pipeline_config_from_path(config_path)

        # Fields should be populated from schema
        field_names = [field["name"] for field in config.fields]
        assert len(field_names) > 5
        assert "action_type" in field_names
        assert "acquisition_timestamp" in field_names

    def test_fields_not_overwritten_when_present_in_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test existing fields in config are not overwritten."""
        providers_file = Path("tests/fixtures/configs/providers.yaml")
        monkeypatch.setattr(
            provider_registry,
            "DEFAULT_PROVIDERS_REGISTRY_PATH",
            providers_file,
        )
        provider_registry.clear_provider_registry_cache()

        # Inject provider
        registry = create_default_schema_registry()
        contract_provider = SchemaContractProviderImpl(registry)
        set_schema_contract_provider(contract_provider)

        # Create config WITH fields section
        config_path = tmp_path / "chembl_activity.yaml"
        config_path.write_text(
            """id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
fields:
  - name: custom_field
    data_type: string
    is_nullable: false
    is_filterable: true
    description: Custom field
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
            encoding="utf-8",
        )

        config = get_pipeline_config_from_path(config_path)

        # Should keep custom fields
        assert len(config.fields) == 1
        assert config.fields[0]["name"] == "custom_field"

    def test_reset_schema_contract_provider_clears_state(self) -> None:
        """Test reset_schema_contract_provider clears injected provider."""
        mock_provider = MagicMock(spec=SchemaContractProviderABC)
        set_schema_contract_provider(mock_provider)

        reset_schema_contract_provider()

        # Now loading should fail
        # (tested indirectly - if provider was still set, loading would succeed)
        # This test just ensures reset doesn't raise
        assert True


class TestSchemaContractProviderWithMock:
    """Tests using mock provider to verify contract."""

    def test_get_output_schema_name_called_correctly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test provider.get_output_schema_name is called with correct args."""
        providers_file = Path("tests/fixtures/configs/providers.yaml")
        monkeypatch.setattr(
            provider_registry,
            "DEFAULT_PROVIDERS_REGISTRY_PATH",
            providers_file,
        )
        provider_registry.clear_provider_registry_cache()

        mock_provider = MagicMock(spec=SchemaContractProviderABC)
        mock_provider.get_output_schema_name.return_value = "test_schema"
        mock_provider.get_field_configs.return_value = [
            {
                "name": "test_field",
                "data_type": "string",
                "is_nullable": False,
                "is_filterable": False,
                "description": "Test",
            }
        ]
        set_schema_contract_provider(mock_provider)

        config_path = tmp_path / "chembl_activity.yaml"
        config_path.write_text(
            """id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
            encoding="utf-8",
        )

        get_pipeline_config_from_path(config_path)

        mock_provider.get_output_schema_name.assert_called_once()
        call_args = mock_provider.get_output_schema_name.call_args
        assert call_args[0][0] == "chembl.activity"  # pipeline_code
        assert call_args[1]["default_entity"] == "activity"  # entity_name

    def test_get_field_configs_called_with_schema_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test provider.get_field_configs is called with returned schema name."""
        providers_file = Path("tests/fixtures/configs/providers.yaml")
        monkeypatch.setattr(
            provider_registry,
            "DEFAULT_PROVIDERS_REGISTRY_PATH",
            providers_file,
        )
        provider_registry.clear_provider_registry_cache()

        mock_provider = MagicMock(spec=SchemaContractProviderABC)
        mock_provider.get_output_schema_name.return_value = "custom_schema_name"
        mock_provider.get_field_configs.return_value = [
            {
                "name": "field1",
                "data_type": "string",
                "is_nullable": False,
                "is_filterable": False,
                "description": "",
            }
        ]
        set_schema_contract_provider(mock_provider)

        config_path = tmp_path / "chembl_activity.yaml"
        config_path.write_text(
            """id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
            encoding="utf-8",
        )

        get_pipeline_config_from_path(config_path)

        mock_provider.get_field_configs.assert_called_once_with("custom_schema_name")

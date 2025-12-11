"""Tests for YAML pipeline contract loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.domain.ports.pipeline_contract_loader import PipelineContractLoaderError
from bioetl.domain.schemas.pipeline_contracts import (
    PipelineSchemaModel,
    clear_contract_loader,
    get_contract_loader,
    get_pipeline_contract,
    has_pipeline_contract,
    list_pipeline_codes,
    set_contract_loader,
)
from bioetl.infrastructure.config.pipeline_contract_loader import (
    YamlPipelineContractLoader,
)


@pytest.fixture
def sample_contracts_yaml(tmp_path: Path) -> Path:
    """Create a sample contracts YAML file."""
    contracts_file = tmp_path / "pipeline_contracts.yaml"
    contracts_file.write_text(
        """
contracts:
  test.entity:
    pipeline_code: test.entity
    schema_out: entity
    schema_in: entity_input
    output_schema: entity_output

  test.another:
    pipeline_code: test.another
    schema_out: another

default_template:
  use_pipeline_code_as_schema: true
  schema_suffix_in: _in
  schema_suffix_out: _out
"""
    )
    return contracts_file


@pytest.fixture
def loader_with_sample(sample_contracts_yaml: Path) -> YamlPipelineContractLoader:
    """Create loader with sample contracts."""
    return YamlPipelineContractLoader(config_path=sample_contracts_yaml)


class TestYamlPipelineContractLoader:
    """Tests for YamlPipelineContractLoader."""

    def test_load_contracts_from_yaml(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test loading contracts from YAML file."""
        contracts = loader_with_sample.load_contracts()

        assert "test.entity" in contracts
        assert "test.another" in contracts
        assert len(contracts) == 2

    def test_get_contract_existing(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test getting an existing contract."""
        contract = loader_with_sample.get_contract("test.entity")

        assert contract.pipeline_code == "test.entity"
        assert contract.schema_out == "entity"
        assert contract.schema_in == "entity_input"
        assert contract.output_schema == "entity_output"

    def test_get_contract_with_defaults(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test contract with optional fields defaulting."""
        contract = loader_with_sample.get_contract("test.another")

        assert contract.pipeline_code == "test.another"
        assert contract.schema_out == "another"
        assert contract.schema_in is None  # Not specified in YAML

    def test_get_contract_unknown_uses_template(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test getting unknown contract uses default template."""
        contract = loader_with_sample.get_contract("unknown.pipeline")

        assert contract.pipeline_code == "unknown.pipeline"
        assert contract.schema_out == "pipeline"
        assert contract.schema_in == "pipeline_in"  # From template
        assert contract.output_schema == "pipeline_out"  # From template

    def test_get_contract_unknown_with_default_entity(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test unknown contract with explicit default_entity."""
        contract = loader_with_sample.get_contract(
            "unknown.x", default_entity="custom_entity"
        )

        assert contract.schema_out == "custom_entity"
        assert contract.schema_in == "custom_entity_in"

    def test_has_contract(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test checking contract existence."""
        assert loader_with_sample.has_contract("test.entity") is True
        assert loader_with_sample.has_contract("unknown.x") is False

    def test_list_pipeline_codes(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test listing all pipeline codes."""
        codes = loader_with_sample.list_pipeline_codes()

        assert sorted(codes) == ["test.another", "test.entity"]

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file returns empty contracts."""
        loader = YamlPipelineContractLoader(
            config_path=tmp_path / "nonexistent.yaml"
        )
        contracts = loader.load_contracts()

        assert contracts == {}

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test invalid YAML raises PipelineContractLoaderError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("contracts: [not a mapping]")

        loader = YamlPipelineContractLoader(config_path=bad_file)

        with pytest.raises(PipelineContractLoaderError, match="Invalid contracts"):
            loader.load_contracts()

    def test_caching_of_loaded_contracts(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test contracts are cached after first load."""
        contracts1 = loader_with_sample.load_contracts()
        contracts2 = loader_with_sample.load_contracts()

        assert contracts1 is contracts2  # Same object (cached)


class TestContractLoaderInjection:
    """Tests for contract loader injection into domain."""

    @pytest.fixture(autouse=True)
    def cleanup_loader(self) -> Any:
        """Clear loader after each test."""
        yield
        clear_contract_loader()

    def test_set_and_get_contract_loader(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test setting and getting contract loader."""
        assert get_contract_loader() is None

        set_contract_loader(loader_with_sample)

        assert get_contract_loader() is loader_with_sample

    def test_clear_contract_loader(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test clearing contract loader."""
        set_contract_loader(loader_with_sample)
        clear_contract_loader()

        assert get_contract_loader() is None

    def test_get_pipeline_contract_uses_injected_loader(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test get_pipeline_contract uses injected loader."""
        set_contract_loader(loader_with_sample)

        contract = get_pipeline_contract("test.entity")

        assert contract.schema_out == "entity"
        assert contract.schema_in == "entity_input"

    def test_get_pipeline_contract_fallback_without_loader(self) -> None:
        """Test get_pipeline_contract falls back to hardcoded when no loader."""
        # Ensure no loader is set
        clear_contract_loader()

        # Should use hardcoded PIPELINE_CONTRACTS
        contract = get_pipeline_contract("chembl.activity")

        assert contract.schema_out == "activity"
        assert contract.schema_in == "activity_input"

    def test_list_pipeline_codes_uses_injected_loader(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test list_pipeline_codes uses injected loader."""
        set_contract_loader(loader_with_sample)

        codes = list_pipeline_codes()

        assert "test.entity" in codes
        assert "chembl.activity" not in codes  # Not in test loader

    def test_has_pipeline_contract_uses_injected_loader(
        self, loader_with_sample: YamlPipelineContractLoader
    ) -> None:
        """Test has_pipeline_contract uses injected loader."""
        set_contract_loader(loader_with_sample)

        assert has_pipeline_contract("test.entity") is True
        assert has_pipeline_contract("chembl.activity") is False


class TestDefaultContractTemplate:
    """Tests for default contract template behavior."""

    def test_no_template_uses_simple_default(self, tmp_path: Path) -> None:
        """Test without template, uses simple entity-based default."""
        contracts_file = tmp_path / "simple.yaml"
        contracts_file.write_text(
            """
contracts:
  test.one:
    pipeline_code: test.one
    schema_out: one
"""
        )
        loader = YamlPipelineContractLoader(config_path=contracts_file)

        contract = loader.get_contract("unknown.entity")

        assert contract.schema_out == "entity"
        assert contract.schema_in == "entity"  # Same as schema_out
        assert contract.output_schema == "entity"


class TestPipelineSchemaModel:
    """Tests for PipelineSchemaModel dataclass."""

    def test_get_output_schema_with_explicit(self) -> None:
        """Test get_output_schema returns explicit output_schema."""
        model = PipelineSchemaModel(
            pipeline_code="test",
            schema_out="out",
            output_schema="explicit_output",
        )

        assert model.get_output_schema() == "explicit_output"

    def test_get_output_schema_fallback(self) -> None:
        """Test get_output_schema falls back to schema_out."""
        model = PipelineSchemaModel(
            pipeline_code="test",
            schema_out="out",
        )

        assert model.get_output_schema() == "out"

    def test_frozen_dataclass(self) -> None:
        """Test PipelineSchemaModel is frozen (immutable)."""
        model = PipelineSchemaModel(
            pipeline_code="test",
            schema_out="out",
        )

        with pytest.raises(AttributeError):
            model.schema_out = "modified"  # type: ignore[misc]

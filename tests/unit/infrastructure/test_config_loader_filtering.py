from unittest.mock import Mock
import pytest

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config_loader_filtering import apply_hierarchical_filter_config

def test_apply_hierarchical_filter_config_missing_provider_entity() -> None:
    config: JsonDict = {}
    entity_config: JsonDict = {}
    filter_loader_mock = Mock(spec=FilterConfigLoader)

    apply_hierarchical_filter_config(
        config=config,
        entity_config=entity_config,
        filter_loader=filter_loader_mock,
    )

    filter_loader_mock.load_as_dict.assert_not_called()

def test_apply_hierarchical_filter_config_no_overrides() -> None:
    config: JsonDict = {"provider": "chembl", "entity_type": "assay"}
    entity_config: JsonDict = {}
    filter_loader_mock = Mock(spec=FilterConfigLoader)

    merged_filters: JsonDict = {
        "input_filter": {"enabled": True},
        "silver_filters": {"required_fields": ["assay_id"]}
    }
    filter_loader_mock.load_as_dict.return_value = merged_filters

    apply_hierarchical_filter_config(
        config=config,
        entity_config=entity_config,
        filter_loader=filter_loader_mock,
    )

    filter_loader_mock.load_as_dict.assert_called_once_with("chembl", "assay", None)

    assert config["input_filter"] == {"enabled": True}
    assert config["silver_filters"] == {"required_fields": ["assay_id"]}

def test_apply_hierarchical_filter_config_with_inline_overrides() -> None:
    config: JsonDict = {"provider": "pubchem", "entity_type": "compound"}
    entity_config: JsonDict = {
        "gold_filters": {"columns": {"type": ["A", "B"]}},
        "filter_rules": {"extraction_params": {"limit": 100}}
    }
    filter_loader_mock = Mock(spec=FilterConfigLoader)

    merged_filters: JsonDict = {
        "gold_filters": {"columns": {"type": ["A", "B"]}},
        "extraction_params": {"limit": 100}
    }
    filter_loader_mock.load_as_dict.return_value = merged_filters

    apply_hierarchical_filter_config(
        config=config,
        entity_config=entity_config,
        filter_loader=filter_loader_mock,
    )

    expected_inline_overrides = {
        "gold_filters": {"columns": {"type": ["A", "B"]}},
        "extraction_params": {"limit": 100}
    }

    filter_loader_mock.load_as_dict.assert_called_once_with(
        "pubchem", "compound", expected_inline_overrides
    )

    assert config["gold_filters"] == {"columns": {"type": ["A", "B"]}}
    assert config["extraction_params"] == {"limit": 100}

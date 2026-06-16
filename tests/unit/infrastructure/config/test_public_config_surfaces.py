"""Tests for public infrastructure config reexport surfaces."""

from __future__ import annotations

import pytest

from bioetl.infrastructure import config as public_config
from bioetl.infrastructure.config._base import Settings as BaseSettings
from bioetl.infrastructure.config._base import get_settings as base_get_settings
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config as direct_load_pipeline_config,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from bioetl.infrastructure.config.settings_api import Settings, get_settings
from bioetl.infrastructure.config.source_config_loader import (
    load_source_config as direct_load_source_config,
)


pytestmark = pytest.mark.unit


def test_settings_api_reexports_settings_surface_from_base_module() -> None:
    """settings_api should remain a narrow alias for the canonical settings owner."""
    assert Settings is BaseSettings
    assert get_settings is base_get_settings


def test_public_config_package_root_reexports_lazy_and_eager_surfaces() -> None:
    """Package root should expose the sanctioned compatibility surface."""
    assert public_config.Settings is BaseSettings
    assert public_config.get_settings is base_get_settings
    assert public_config.PipelineConfigLoader is PipelineConfigLoader
    assert public_config.load_pipeline_config is direct_load_pipeline_config
    assert public_config.load_source_config is direct_load_source_config


def test_public_config_package_root_rejects_unknown_attribute() -> None:
    """Unknown compatibility surface names must still fail loudly."""
    with pytest.raises(AttributeError, match="does_not_exist"):
        getattr(public_config, "does_not_exist")

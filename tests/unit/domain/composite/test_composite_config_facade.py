"""Tests for composite config compatibility facade."""

from __future__ import annotations

import pytest

from pathlib import Path

from bioetl.domain.composite import config as facade
from bioetl.domain.composite.config_models import (
    CrossValidationConfig as ModelsCrossValidationConfig,
)
from bioetl.domain.composite.config_models import (
    DataSchemaConfig as ModelsDataSchemaConfig,
)
from bioetl.domain.composite.config_models import (
    DependencyConfig as ModelsDependencyConfig,
)
from bioetl.domain.composite.config_models import (
    EnricherConfig as ModelsEnricherConfig,
)
from bioetl.domain.composite.config_models import (
    LayerColumnConfig as ModelsLayerColumnConfig,
)
from bioetl.domain.composite.config_models import SeedConfig as ModelsSeedConfig


pytestmark = pytest.mark.unit

def test_config_facade_keeps_model_reexports() -> None:
    assert facade.SeedConfig is ModelsSeedConfig
    assert facade.DependencyConfig is ModelsDependencyConfig
    assert facade.EnricherConfig is ModelsEnricherConfig
    assert facade.LayerColumnConfig is ModelsLayerColumnConfig
    assert facade.DataSchemaConfig is ModelsDataSchemaConfig
    assert facade.CrossValidationConfig is ModelsCrossValidationConfig


def test_config_facade_file_is_thin() -> None:
    config_path = Path("src/bioetl/domain/composite/config.py")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 300


def test_config_facade_does_not_reexport_private_validators() -> None:
    for name in (
        "_validate_positive",
        "_validate_positive_limit",
        "_validate_optional_threshold",
        "_validate_threshold_order",
    ):
        assert not hasattr(facade, name)

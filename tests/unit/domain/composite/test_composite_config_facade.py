"""Tests for composite config compatibility facade."""

from __future__ import annotations

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

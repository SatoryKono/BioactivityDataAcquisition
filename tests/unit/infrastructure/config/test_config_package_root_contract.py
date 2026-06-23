"""Unit contracts for the infrastructure config package-root facade."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_config_package_root_lazy_exports_canonical_loader_functions() -> None:
    """Lazy package-root exports must resolve to canonical loader modules."""
    import bioetl.infrastructure.config as config
    from bioetl.infrastructure.config.composite_config_api import load_composite_config
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
    from bioetl.infrastructure.config.source_config_loader import load_source_config
    from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

    assert config.__getattr__("load_pipeline_config") is load_pipeline_config
    assert config.__getattr__("load_composite_config") is load_composite_config
    assert config.__getattr__("load_source_config") is load_source_config
    assert config.__getattr__("load_workflow_config") is load_workflow_config


def test_config_package_root_rejects_unknown_lazy_export() -> None:
    """Unknown config package-root symbols must fail fast."""
    import bioetl.infrastructure.config as config

    with pytest.raises(AttributeError, match="not_a_config_export"):
        config.__getattr__("not_a_config_export")

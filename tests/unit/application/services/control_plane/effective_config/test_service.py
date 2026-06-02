"""Contract tests for the effective-config service seam."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane import effective_config
from bioetl.application.services.control_plane.effective_config.service import (
    EffectiveConfigService,
)


pytestmark = pytest.mark.unit


def test_service_module_exports_effective_config_service() -> None:
    assert effective_config.EffectiveConfigService is EffectiveConfigService
    assert effective_config.__all__ == ["EffectiveConfigService"]

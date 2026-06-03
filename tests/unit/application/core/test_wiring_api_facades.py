"""Unit tests for wiring API facade modules.

These are legacy flat facades for composition-owned modules.
Tests verify that imports work correctly.
"""

from __future__ import annotations

import pytest


class TestPipelineRegistryWiringApi:
    """Tests for pipeline_registry_wiring_api facade."""

    def test_pipeline_registry_wiring_api_imports(self):
        """Test that pipeline_registry_wiring_api imports successfully."""
        # This test verifies that the facade can import from wiring.registry
        # If the import fails, the test will raise an ImportError
        from bioetl.application.core.pipeline_registry_wiring_api import (  # noqa: F401
            ActivityTransformer,
        )

        # Verify that the imported class is a class
        assert isinstance(ActivityTransformer, type)


class TestTransformerWiringApi:
    """Tests for transformer_wiring_api facade."""

    def test_transformer_wiring_api_imports(self):
        """Test that transformer_wiring_api imports successfully."""
        # This test verifies that the facade can import from wiring.transformer
        # If the import fails, the test will raise an ImportError
        from bioetl.application.core.transformer_wiring_api import (  # noqa: F401
            BaseTransformer,
        )

        # Verify that the imported class is a class
        assert isinstance(BaseTransformer, type)


pytestmark = pytest.mark.unit


# Import modules to ensure they're covered
from bioetl.application.core import pipeline_registry_wiring_api  # noqa: F401
from bioetl.application.core import transformer_wiring_api  # noqa: F401

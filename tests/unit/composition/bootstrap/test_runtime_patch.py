"""Unit tests for runtime bootstrap patching."""

from __future__ import annotations

import pytest

from unittest.mock import patch

from bioetl.composition.bootstrap.runtime.pipeline import (
    apply_runtime_compatibility_patches,
)


pytestmark = pytest.mark.unit


def test_apply_runtime_compatibility_patches_delegates_to_pandera_compat() -> None:
    """Runtime compatibility entrypoint should delegate to the canonical compat shim."""
    with patch(
        "bioetl.composition.bootstrap.runtime.pipeline.apply_pandera_typing_compat_if_needed",
        return_value=True,
    ) as mock_apply:
        result = apply_runtime_compatibility_patches()

    assert result is True
    mock_apply.assert_called_once_with()

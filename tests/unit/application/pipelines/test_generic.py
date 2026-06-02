"""Same-path owner tests for generic pipeline module."""

from __future__ import annotations

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.generic import GenericPipeline, __all__


pytestmark = pytest.mark.unit


def test_generic_pipeline_is_public_subclass_of_base_pipeline() -> None:
    assert issubclass(GenericPipeline, BasePipeline)


def test_generic_pipeline_module_exports_canonical_surface() -> None:
    assert __all__ == ["GenericPipeline"]

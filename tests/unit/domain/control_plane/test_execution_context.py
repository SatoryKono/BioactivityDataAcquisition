"""Tests for control-plane execution-context helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.control_plane.execution_context import is_composite_execution_context


pytestmark = pytest.mark.unit


def test_is_composite_execution_context_detects_composite_manifest() -> None:
    manifest = SimpleNamespace(launch_context={"execution_context": "composite"})

    assert is_composite_execution_context(manifest) is True


def test_is_composite_execution_context_treats_missing_context_as_source() -> None:
    manifest = SimpleNamespace(launch_context={})

    assert is_composite_execution_context(manifest) is False

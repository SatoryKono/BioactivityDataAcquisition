"""Unit tests for pipeline execution entrypoints."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from bioetl.composition._pipeline_execution import _ensure_registrations

pytestmark = pytest.mark.unit


def test_ensure_registrations_calls_ensure_runtime_registrations_with_none() -> None:
    """Test that _ensure_registrations passes registry=None by default."""
    with patch(
        "bioetl.composition._registration.ensure_runtime_registrations"
    ) as mock_ensure:
        _ensure_registrations()

    mock_ensure.assert_called_once_with(registry=None)


def test_ensure_registrations_calls_ensure_runtime_registrations_with_registry() -> (
    None
):
    """Test that _ensure_registrations passes the provided registry."""
    mock_registry = Mock()
    with patch(
        "bioetl.composition._registration.ensure_runtime_registrations"
    ) as mock_ensure:
        _ensure_registrations(registry=mock_registry)

    mock_ensure.assert_called_once_with(registry=mock_registry)

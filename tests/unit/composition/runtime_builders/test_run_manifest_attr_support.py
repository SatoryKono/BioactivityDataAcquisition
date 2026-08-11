# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Focused coverage for run-manifest attribute helpers (#8614)."""

from __future__ import annotations

pytestmark = pytest.mark.unit

from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders._run_manifest_attr_support import read_attr


def test_read_attr_without_default_returns_existing_value() -> None:
    host = SimpleNamespace(pipeline="activity")
    assert read_attr(host, "pipeline") == "activity"


def test_read_attr_without_default_raises_for_missing_attr() -> None:
    host = SimpleNamespace()
    with pytest.raises(AttributeError):
        read_attr(host, "missing")


def test_read_attr_with_default_returns_default_for_missing_attr() -> None:
    host = SimpleNamespace()
    assert read_attr(host, "missing", default="fallback") == "fallback"


def test_read_attr_with_default_returns_existing_value() -> None:
    host = SimpleNamespace(value=7)
    assert read_attr(host, "value", default=0) == 7

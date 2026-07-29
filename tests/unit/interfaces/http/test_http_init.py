# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for the HTTP package root surface."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_http_package_root_exposes_no_convenience_exports() -> None:
    """Package root should stay free of convenience re-exports."""
    module = importlib.import_module("bioetl.interfaces.http")

    assert module.__all__ == []
    assert "HealthResponse" not in dir(module)
    assert "HealthServer" not in dir(module)
    with pytest.raises(AttributeError):
        module.HealthResponse()
    with pytest.raises(AttributeError):
        module.HealthServer()

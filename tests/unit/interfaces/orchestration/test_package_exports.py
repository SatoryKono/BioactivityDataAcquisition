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
"""Tests for the retired interfaces.orchestration package seam."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_orchestration_package_is_retired() -> None:
    """Placeholder orchestration package must not remain importable."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.interfaces.orchestration")

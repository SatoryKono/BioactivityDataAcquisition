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
"""Focused unit tests for the top-level domain lazy facade."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_domain_lazy_module_export_is_cached() -> None:
    """Module exports should resolve once and then stay cached on the facade."""
    import bioetl.domain as domain

    domain.__dict__.pop("workflow", None)

    workflow_module = domain.__getattr__("workflow")

    assert workflow_module.__name__ == "bioetl.domain.workflow"
    assert domain.workflow is workflow_module


def test_domain_lazy_attribute_export_is_cached() -> None:
    """Attribute exports should resolve from their owner module and cache locally."""
    import bioetl.domain as domain
    from bioetl.domain.version import get_version

    domain.__dict__.pop("get_version", None)

    resolved = domain.__getattr__("get_version")

    assert resolved is get_version
    assert domain.get_version is get_version


def test_domain_lazy_facade_dir_and_unknown_export_are_deterministic() -> None:
    """The facade exposes declared lazy names and rejects implicit compat seams."""
    import bioetl.domain as domain

    exported = dir(domain)

    assert "workflow" in exported
    assert "get_version" in exported
    assert "DomainEventObservabilityEnvelope" in exported
    missing_name = "not_a_domain_export"
    with pytest.raises(AttributeError, match=missing_name):
        getattr(domain, missing_name)

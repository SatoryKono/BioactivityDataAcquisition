"""Owner tests for the pip-audit dependency-consumer anchor."""

from __future__ import annotations

from scripts.engineering.ci.pip_audit_owner import PIP_AUDIT_OWNER


def test_pip_audit_owner_distribution_keyword_is_literal() -> None:
    """Lock bumps for msgpack/cachecontrol resolve through this distribution pin."""
    assert PIP_AUDIT_OWNER.distribution == "pip-audit"
    assert PIP_AUDIT_OWNER.import_name == "pip_audit"

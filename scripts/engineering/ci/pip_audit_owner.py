"""Pinned pip-audit identity for Python dependency-consumer routing.

msgpack is a transitive of pip-audit's cachecontrol stack. Lock bumps that
touch msgpack must resolve to a declared distribution named via a literal
``distribution=`` keyword (see ``_python_dependency_changes``). This module
is that reviewed owner anchor — not a runtime CLI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipAuditOwner:
    """Stable distribution pin for dependency-route confirmation."""

    distribution: str
    import_name: str


PIP_AUDIT_OWNER = PipAuditOwner(
    distribution="pip-audit",
    import_name="pip_audit",
)

"""Public seam for canonical storage-audit wiring helpers."""

from __future__ import annotations

from bioetl.composition.factories.storage._audit import create_audit_port

__all__ = ["create_audit_port"]

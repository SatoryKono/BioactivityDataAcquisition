"""Backward-compatible re-export for `bioetl.composition.factories.storage.audit`."""

from __future__ import annotations

from bioetl.composition.factories.storage import audit as _public

create_audit_port = _public.create_audit_port

__all__ = ['create_audit_port']

"""Application-owned replay-taxonomy field definitions."""

from __future__ import annotations

from bioetl.domain.control_plane import replay_taxonomy_fields as _domain_fields

LIST_DEFAULTS = _domain_fields.LIST_DEFAULTS
REPLAY_TAXONOMY_FIELDS = _domain_fields.REPLAY_TAXONOMY_FIELDS

__all__ = ["LIST_DEFAULTS", "REPLAY_TAXONOMY_FIELDS"]

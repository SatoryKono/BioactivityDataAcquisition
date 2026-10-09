"""Compatibility facade for replay-taxonomy field definitions."""

from bioetl.domain.control_plane.replay_taxonomy_fields import (
    LIST_DEFAULTS as LIST_DEFAULTS,
)
from bioetl.domain.control_plane.replay_taxonomy_fields import (
    REPLAY_TAXONOMY_FIELDS as REPLAY_TAXONOMY_FIELDS,
)

__all__ = ["LIST_DEFAULTS", "REPLAY_TAXONOMY_FIELDS"]

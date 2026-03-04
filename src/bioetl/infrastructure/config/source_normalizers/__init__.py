"""Source configuration normalizers.

Isolates backward-compatibility migration logic from core loaders.
"""

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = [
    "normalize_source_config",
]

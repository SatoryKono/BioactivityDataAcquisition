"""Compatibility re-export for legacy source normalizer path.

Canonical implementation lives in ``bioetl.infrastructure.legacy_normalizers``.
"""

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = ["normalize_source_config"]

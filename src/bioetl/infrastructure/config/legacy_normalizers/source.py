"""Compatibility re-export for legacy source config normalization.

This module remains importable to preserve backward compatibility:
``bioetl.infrastructure.config.legacy_normalizers.source``.
Implementation lives in leaf package ``bioetl.infrastructure.legacy_normalizers``.
"""

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = ["normalize_source_config"]

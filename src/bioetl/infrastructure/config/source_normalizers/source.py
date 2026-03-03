"""Compatibility re-export for source config normalization.

This module remains importable to preserve backward compatibility:
``bioetl.infrastructure.config.source_normalizers.source``.
Implementation lives in leaf package ``bioetl.infrastructure.source_normalizers``.
"""

from bioetl.infrastructure.source_normalizers.source import normalize_source_config

__all__ = ["normalize_source_config"]

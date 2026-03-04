"""Compatibility package for source-config normalizer imports.

Canonical legacy migration logic lives in
``bioetl.infrastructure.legacy_normalizers``.
"""

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = ["normalize_source_config"]

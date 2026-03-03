"""Leaf legacy normalizers for infrastructure config loading.

This package intentionally lives outside ``infrastructure.config`` to avoid
import-time cycles when loading ``bioetl.infrastructure.config_loader``.
"""

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = ["normalize_source_config"]

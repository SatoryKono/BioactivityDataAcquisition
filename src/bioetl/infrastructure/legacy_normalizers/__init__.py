"""Legacy configuration normalizers.

This package contains migration logic for backward-compatible config formats.
Core config loaders orchestrate read/normalize/validate/map and delegate
legacy-specific transformations to this package.
"""

from bioetl.infrastructure.legacy_normalizers.pipeline import (
    apply_pipeline_schema_normalization,
)
from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config

__all__ = ["apply_pipeline_schema_normalization", "normalize_source_config"]

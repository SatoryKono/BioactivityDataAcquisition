"""DEPRECATED: Normalization config moved to pipeline_options.py.

This module is deprecated and will be removed in v3.0.
Import from bioetl.domain.configs.pipeline_options instead:

    from bioetl.domain.configs.pipeline_options import NormalizationConfig
"""

from __future__ import annotations

import warnings

from bioetl.domain.configs.pipeline_options import NormalizationConfig

warnings.warn(
    "bioetl.domain.configs.normalization is deprecated. "
    "Import from bioetl.domain.configs.pipeline_options instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["NormalizationConfig"]

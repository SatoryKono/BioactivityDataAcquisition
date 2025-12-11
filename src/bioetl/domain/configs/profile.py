"""DEPRECATED: Profile config moved to pipeline_options.py.

This module is deprecated and will be removed in v3.0.
Import from bioetl.domain.configs.pipeline_options instead:

    from bioetl.domain.configs.pipeline_options import ProfileConfig
"""

from __future__ import annotations

import warnings

from bioetl.domain.configs.pipeline_options import ProfileConfig

warnings.warn(
    "bioetl.domain.configs.profile is deprecated. "
    "Import from bioetl.domain.configs.pipeline_options instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ProfileConfig"]

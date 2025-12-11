"""Deprecated. Use bioetl.application.bootstrap_factory instead."""
from __future__ import annotations

import warnings

warnings.warn(
    "bioetl.interfaces.bootstrap_factory is deprecated. "
    "Use bioetl.application.bootstrap_factory instead.",
    DeprecationWarning,
    stacklevel=2,
)

from bioetl.application.bootstrap_factory import create_default_bootstrap

__all__ = ["create_default_bootstrap"]

"""Compatibility re-export — implementation lives in `bioetl.application.services.ops.admin_runtime_api`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.ops.admin_runtime_api import *  # noqa: F403
from bioetl.application.services.ops.admin_runtime_api import __all__ as __all__

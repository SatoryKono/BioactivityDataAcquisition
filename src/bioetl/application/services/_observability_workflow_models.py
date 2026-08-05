"""Compatibility re-export — implementation lives in `bioetl.application.services.workflow._observability_workflow_models`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.workflow._observability_workflow_models import *  # noqa: F403
from bioetl.application.services.workflow._observability_workflow_models import __all__ as __all__

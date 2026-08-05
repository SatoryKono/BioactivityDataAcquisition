"""Compatibility re-export — implementation lives in `bioetl.application.services.quality.dq_report_models`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.quality.dq_report_models import *  # noqa: F403
from bioetl.application.services.quality.dq_report_models import __all__ as __all__

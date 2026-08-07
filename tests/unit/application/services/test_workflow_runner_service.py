"""Compatibility path for ChemblBaseline smoke (CI-C1-010 / #8265).

Canonical tests live under ``tests/unit/repo_backed/application/services/``.
This module re-exports them so workflow path filters and pytest invocation
that still reference the historical location keep working.
"""

from __future__ import annotations

# Re-export the full suite from the canonical location.
from tests.unit.repo_backed.application.services.test_workflow_runner_service import *  # noqa: F403

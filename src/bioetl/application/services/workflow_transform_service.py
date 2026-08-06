"""Compatibility re-export — implementation lives in `bioetl.application.services.workflow.workflow_transform_service`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""

from __future__ import annotations

from bioetl.application.services.workflow.workflow_transform_service import *  # noqa: F403
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformDestructiveCommit as WorkflowTransformDestructiveCommit,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    __all__ as __all__,
)

"""Public compatibility entrypoint for composite merge services."""

from __future__ import annotations

__all__ = ["MergeCollaboratorGroup", "MergeService", "_path_to_table_name"]

from bioetl.application.composite.merge_service import (
    MergeService,
    _path_to_table_name,
)
from bioetl.application.composite.merger_collaborators import (
    MergeCollaboratorGroup,
)

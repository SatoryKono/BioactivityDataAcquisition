"""Domain context objects."""

from dataclasses import dataclass
from logging import Logger

from bioetl.domain.types import RunID, RunType


@dataclass(frozen=True)
class PipelineContext:
    """Context object for a pipeline run.

    Provides a consistent set of metadata to all pipeline components.
    """

    run_id: RunID
    run_type: RunType
    logger: Logger

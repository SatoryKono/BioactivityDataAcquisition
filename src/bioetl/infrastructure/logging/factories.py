"""Factories for progress reporters.

Naming convention:
- create_*() - creates a new instance each time
"""

from bioetl.domain.observability import ProgressReporterABC
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)


def create_progress_reporter() -> ProgressReporterABC:
    """Create a new progress reporter instance (tqdm)."""
    return TqdmProgressReporterImpl()

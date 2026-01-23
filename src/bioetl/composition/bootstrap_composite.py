"""Bootstrap functions for Composite Pipeline.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from composition/bootstrap/runtime/ instead:

    from bioetl.composition.bootstrap.runtime import (
        bootstrap_composite_pipeline,
        load_composite_config,
    )

See ADR-026 for architectural decisions on composite pipelines.
"""

from __future__ import annotations

# Re-export from the new bootstrap package for backward compatibility
from bioetl.application.composite.runner import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_pipeline,
    load_composite_config,
)

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_pipeline",
    "load_composite_config",
]

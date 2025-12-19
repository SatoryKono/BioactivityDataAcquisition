"""Pipeline configuration - backward compatibility re-exports.

DEPRECATED: Import from bioetl.domain.config instead.

This module re-exports PipelineRuntimeConfig from the consolidated location
for backward compatibility. New code should import directly from
bioetl.domain.config.

Part of BasePipeline decomposition (ADR-0005).
"""

# Re-export for backward compatibility
from bioetl.domain.config import (
    PipelineRuntimeConfig,
    RuntimeConfig,
)

__all__ = ["PipelineRuntimeConfig", "RuntimeConfig"]

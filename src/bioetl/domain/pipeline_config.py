"""Pipeline configuration - backward compatibility re-exports.

DEPRECATED: Import from bioetl.domain.config instead.

This module re-exports PipelineConfig from the consolidated location
for backward compatibility. New code should import directly from
bioetl.domain.config.
"""

# Re-export for backward compatibility
from bioetl.domain.config import PipelineConfig

__all__ = ["PipelineConfig"]

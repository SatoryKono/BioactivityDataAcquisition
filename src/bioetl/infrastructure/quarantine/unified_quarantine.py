"""Backward compatibility shim for unified quarantine.

Re-exports UnifiedQuarantine from the new modular location.
Import from `bioetl.infrastructure.quarantine` instead.
"""

from bioetl.infrastructure.quarantine.helpers import quote_literal as _quote_literal
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantine

__all__ = ["UnifiedQuarantine", "_quote_literal"]

"""Quarantine (Dead Letter Queue) adapters.

Implements RULES.md §2.6 - Quarantine Policy.
"""

from bioetl.infrastructure.quarantine.unified import UnifiedQuarantine

__all__ = ["UnifiedQuarantine"]

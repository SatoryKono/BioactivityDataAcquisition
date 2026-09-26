"""Quarantine (Dead Letter Queue) adapters.

Implements RULES.md §2.6 - Quarantine Policy.
"""

from __future__ import annotations

from bioetl.infrastructure.quarantine.record_encoding import quote_literal
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

__all__ = ["UnifiedQuarantineAdapter", "quote_literal"]

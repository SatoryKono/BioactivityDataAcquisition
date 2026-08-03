"""Infrastructure layer - adapters and implementations.

Contains concrete implementations for domain ports:
- HTTP adapters (ChEMBL, PubChem, etc.)
- Storage adapters (Local filesystem, Delta Lake)
- Locking adapters (Memory lock)
- Metrics exporters (Prometheus)

See RULES.md Section 1.1 for architecture details.
"""

from __future__ import annotations

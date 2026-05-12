"""Owner package for composition bootstrap modules.

The package remains importable so ``bioetl.composition.bootstrap.*`` owner modules
keep a stable namespace, but first-party callers must import concrete owner modules
directly instead of relying on package-root re-exports.
"""

from __future__ import annotations

__all__: list[str] = []

"""Internal pipeline factory support helpers (not a public import path).

Implementations live here so ``composition_factories_pipeline`` can keep a lower
``helper_function_ratio``. This package is composition-internal: do not document
or promote it as a stable public API. Prefer the thin re-export shims under
``bioetl.composition.factories.pipeline`` when a public seam is required.
"""

from __future__ import annotations

__all__: list[str] = []

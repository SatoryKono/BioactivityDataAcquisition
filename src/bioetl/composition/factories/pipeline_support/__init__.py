"""Pipeline factory support helpers extracted from the pipeline hotspot family.

Implementations live here so ``composition_factories_pipeline`` can keep a lower
``helper_function_ratio``. Public call sites may import either this package or
the thin re-export shims under ``factories.pipeline``.
"""

from __future__ import annotations

__all__: list[str] = []

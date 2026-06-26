"""Declarative extraction blocks for PubMed publication pipeline."""

from __future__ import annotations

import bioetl.application.pipelines.pubmed.block_definitions as _blocks

__all__ = list(_blocks.__all__)

for _name in __all__:
    globals()[_name] = getattr(_blocks, _name)

del _name

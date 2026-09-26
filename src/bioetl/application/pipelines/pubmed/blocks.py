# basedpyright residual burn-down (shrink-only product surface).
"""Declarative extraction blocks for PubMed publication pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bioetl.application.pipelines.pubmed.block_definitions as _blocks

if TYPE_CHECKING:
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedAuthorBlock as _PubMedAuthorBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedClassificationBlock as _PubMedClassificationBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedCoreBlock as _PubMedCoreBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedDateBlock as _PubMedDateBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedIdentifierBlock as _PubMedIdentifierBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedJournalBlock as _PubMedJournalBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedMetricsBlock as _PubMedMetricsBlock,
    )
    from bioetl.application.pipelines.pubmed.block_definitions import (
        _PubMedXmlBlock as _PubMedXmlBlock,
    )

__all__ = list(_blocks.__all__)

for _name in __all__:
    globals()[_name] = getattr(_blocks, _name)

del _name  # pyright: ignore[reportPossiblyUnboundVariable]

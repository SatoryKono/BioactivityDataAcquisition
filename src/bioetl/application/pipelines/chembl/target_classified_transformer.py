"""Schema 3.1 target transformer selected only by the enrich profile."""

from __future__ import annotations

from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.domain.entities.chembl_target_classification import TargetV31


class TargetClassifiedTransformer(TargetTransformer):
    """Keep the legacy target entity and optional-classified entity separate."""

    entity_class = TargetV31


__all__ = ["TargetClassifiedTransformer"]

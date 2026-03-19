"""Compatibility facade for split pipeline-construction helpers.

Canonical transformer instantiation now lives in ``TransformerBuilder.build``,
where the pipeline-construction path resolves ``transformer_class(...)`` before
the assembled pipeline receives ``transformer=transformer``.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.config_resolution import (
    DomainConfigResolver,
)
from bioetl.composition.factories.pipeline.construction_types import (
    ContractPolicyLoader,
    DomainConfigMapper,
    EntityTypeExtractor,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)

# Architecture marker: the construction path ultimately instantiates
# ``transformer_class(...)`` inside ``TransformerBuilder.build``.

__all__ = [
    "ContractPolicyLoader",
    "DomainConfigMapper",
    "DomainConfigResolver",
    "EntityTypeExtractor",
    "RunContextFactory",
    "TransformerBuilder",
]

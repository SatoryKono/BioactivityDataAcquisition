"""Public pipeline-construction helper exports.

Transformer instantiation lives in ``TransformerBuilder.build``, while this
module remains the sanctioned aggregate seam for construction helpers.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.construction_types import (
    ContractPolicyLoader,
    DomainConfigMapper,
)
from bioetl.composition.factories.pipeline.entity_type_extractor import (
    EntityTypeExtractor,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.infrastructure.config.domain_config_resolver import (
    DomainConfigResolver,
    resolve_domain_pipeline_config,
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
    "resolve_domain_pipeline_config",
]

"""Static typing surface for the lazy transformer wiring facade."""

from bioetl.application.core.base_transformer import (
    BaseTransformer as BaseTransformer,
)
from bioetl.application.core.base_transformer import (
    TransformerDependencyContext as TransformerDependencyContext,
)
from bioetl.application.core.base_transformer.contract_policy import (
    DefaultContractPolicy as DefaultContractPolicy,
)
from bioetl.application.core.base_transformer.structural_policy import (
    NoOpStructuralPolicy as NoOpStructuralPolicy,
)
from bioetl.application.core.base_transformer.structural_policy import (
    StructuralPolicyProtocol as StructuralPolicyProtocol,
)
from bioetl.application.core.base_transformer.structural_policy import (
    build_structural_policy as build_structural_policy,
)

__all__: list[str]

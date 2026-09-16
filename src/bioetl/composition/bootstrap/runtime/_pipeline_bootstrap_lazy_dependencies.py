"""Policy and registry dependencies for pipeline bootstrap phases."""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_protein_class_target_type_mapping,
    initialize_publication_type_classification,
)
from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
    initialize_chembl_policy_registry,
)
from bioetl.composition.bootstrap.runtime.publication_vocab_init import (
    initialize_publication_controlled_vocabulary,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines

__all__ = [
    "initialize_chembl_policy_registry",
    "initialize_protein_class_target_type_mapping",
    "initialize_publication_controlled_vocabulary",
    "initialize_publication_type_classification",
    "register_all_pipelines",
]

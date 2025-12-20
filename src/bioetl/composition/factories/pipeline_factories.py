# src/bioetl/composition/factories/pipeline_factories.py
"""Consolidated pipeline factory registration.

This module creates and registers all pipeline factories using the
GenericPipelineFactory pattern. This replaces the legacy class-based
factories (chembl_activity.py, pubchem_compound.py, etc.).

Usage:
    Import this module to ensure all pipelines are registered:
    >>> import bioetl.composition.factories.pipeline_factories
"""

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.generic_factory import GenericPipelineFactory
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)
from bioetl.infrastructure.schemas.gold import (
    ChEMBLActivityGoldSchema,
    PubChemCompoundGoldSchema,
    UniProtProteinGoldSchema,
    PubMedPublicationGoldSchema,
)

# ChEMBL Activity Pipeline
chembl_activity_factory = GenericPipelineFactory(
    pipeline_name="chembl_activity",
    pipeline_class=ChEMBLActivityPipeline,
    provider="chembl",
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
    gold_schema=ChEMBLActivityGoldSchema,
)

# PubChem Compound Pipeline
pubchem_compound_factory = GenericPipelineFactory(
    pipeline_name="pubchem_compound",
    pipeline_class=PubChemCompoundPipeline,
    provider="pubchem",
    silver_schema=PUBCHEM_COMPOUND_SCHEMA,
    gold_schema=PubChemCompoundGoldSchema,
)

# UniProt Protein Pipeline
uniprot_protein_factory = GenericPipelineFactory(
    pipeline_name="uniprot_protein",
    pipeline_class=UniProtProteinPipeline,
    provider="uniprot",
    silver_schema=UNIPROT_PROTEIN_SCHEMA,
    gold_schema=UniProtProteinGoldSchema,
)

# PubMed Publications Pipeline
pubmed_publications_factory = GenericPipelineFactory(
    pipeline_name="pubmed_publications",
    pipeline_class=PubMedPublicationsPipeline,
    provider="pubmed",
    silver_schema=PUBMED_PUBLICATION_SCHEMA,
    gold_schema=PubMedPublicationGoldSchema,
)

# All factories for explicit registration
_ALL_FACTORIES = [
    chembl_activity_factory,
    pubchem_compound_factory,
    uniprot_protein_factory,
    pubmed_publications_factory,
]


def register_all_pipelines() -> None:
    """Explicitly register all pipeline factories.

    Call this function once at application startup (e.g., in bootstrap).
    Idempotent: safe to call multiple times.

    Example:
        >>> from bioetl.composition.factories.pipeline_factories import register_all_pipelines
        >>> register_all_pipelines()
        >>> PipelineRegistry.list_pipelines()
        ['chembl_activity', 'pubchem_compound', 'uniprot_protein', 'pubmed_publications']
    """
    if PipelineRegistry.is_initialized():
        return  # Already registered

    for factory in _ALL_FACTORIES:
        PipelineRegistry.register_factory(factory)


__all__ = [
    "chembl_activity_factory",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "register_all_pipelines",
    "uniprot_protein_factory",
]

# src/bioetl/composition/factories/pipeline_factories.py
"""Consolidated pipeline factory definitions.

This module creates all pipeline factories using the GenericPipelineFactory
pattern. Registration is explicit via register_all_pipelines().

Usage:
    >>> from bioetl.composition.factories.pipeline_factories import register_all_pipelines
    >>> register_all_pipelines()  # Call once at application startup
"""

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.application.pipelines.chembl.target_component import (
    ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.composition.factories.generic_factory import GenericPipelineFactory
from bioetl.composition.registry import PipelineRegistry
from bioetl.infrastructure.schemas.gold import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_DOCUMENT_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

# Flag to track if registration has been performed
_factories_registered = False

# ChEMBL Activity Pipeline
chembl_activity_factory = GenericPipelineFactory(
    pipeline_name="chembl_activity",
    pipeline_class=ChEMBLActivityPipeline,
    provider="chembl",
    transformer_class=ActivityTransformer,
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
    gold_schema=ChEMBLActivityGoldSchema,
)

# ChEMBL Assay Pipeline
chembl_assay_factory = GenericPipelineFactory(
    pipeline_name="chembl_assay",
    pipeline_class=ChEMBLAssayPipeline,
    provider="chembl",
    transformer_class=AssayTransformer,
    silver_schema=CHEMBL_ASSAY_SCHEMA,
    gold_schema=ChEMBLAssayGoldSchema,
)

# ChEMBL Document Pipeline
chembl_document_factory = GenericPipelineFactory(
    pipeline_name="chembl_document",
    pipeline_class=ChEMBLDocumentPipeline,
    provider="chembl",
    transformer_class=DocumentTransformer,
    silver_schema=CHEMBL_DOCUMENT_SCHEMA,
    gold_schema=ChEMBLDocumentGoldSchema,
)

# ChEMBL Target Pipeline
chembl_target_factory = GenericPipelineFactory(
    pipeline_name="chembl_target",
    pipeline_class=ChEMBLTargetPipeline,
    provider="chembl",
    transformer_class=TargetTransformer,
    silver_schema=CHEMBL_TARGET_SCHEMA,
    gold_schema=ChEMBLTargetGoldSchema,
)

# ChEMBL Target Component Pipeline
chembl_target_component_factory = GenericPipelineFactory(
    pipeline_name="chembl_target_component",
    pipeline_class=ChEMBLTargetComponentPipeline,
    provider="chembl",
    transformer_class=TargetComponentTransformer,
    silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
    gold_schema=ChEMBLTargetComponentGoldSchema,
)

# ChEMBL Molecule Pipeline
chembl_molecule_factory = GenericPipelineFactory(
    pipeline_name="chembl_molecule",
    pipeline_class=ChEMBLMoleculePipeline,
    provider="chembl",
    transformer_class=MoleculeTransformer,
    silver_schema=CHEMBL_MOLECULE_SCHEMA,
    gold_schema=ChEMBLMoleculeGoldSchema,
)

# PubChem Compound Pipeline
pubchem_compound_factory = GenericPipelineFactory(
    pipeline_name="pubchem_compound",
    pipeline_class=PubChemCompoundPipeline,
    provider="pubchem",
    transformer_class=PubChemCompoundTransformer,
    silver_schema=PUBCHEM_COMPOUND_SCHEMA,
    gold_schema=PubChemCompoundGoldSchema,
)

# UniProt Protein Pipeline
uniprot_protein_factory = GenericPipelineFactory(
    pipeline_name="uniprot_protein",
    pipeline_class=UniProtProteinPipeline,
    provider="uniprot",
    transformer_class=UniProtProteinTransformer,
    silver_schema=UNIPROT_PROTEIN_SCHEMA,
    gold_schema=UniProtProteinGoldSchema,
)

# PubMed Publications Pipeline
pubmed_publications_factory = GenericPipelineFactory(
    pipeline_name="pubmed_publications",
    pipeline_class=PubMedPublicationsPipeline,
    provider="pubmed",
    transformer_class=PubMedPublicationTransformer,
    silver_schema=PUBMED_PUBLICATION_SCHEMA,
    gold_schema=PubMedPublicationGoldSchema,
)


def register_all_pipelines() -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    This function is idempotent - calling it multiple times has no effect
    after the first call.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    global _factories_registered

    if _factories_registered:
        return

    PipelineRegistry.register_factory(chembl_activity_factory)
    PipelineRegistry.register_factory(chembl_assay_factory)
    PipelineRegistry.register_factory(chembl_document_factory)
    PipelineRegistry.register_factory(chembl_target_factory)
    PipelineRegistry.register_factory(chembl_target_component_factory)
    PipelineRegistry.register_factory(chembl_molecule_factory)
    PipelineRegistry.register_factory(pubchem_compound_factory)
    PipelineRegistry.register_factory(uniprot_protein_factory)
    PipelineRegistry.register_factory(pubmed_publications_factory)

    _factories_registered = True


def is_registered() -> bool:
    """Check if factories have been registered.

    Returns:
        True if register_all_pipelines() has been called.
    """
    return _factories_registered


__all__ = [
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_document_factory",
    "chembl_molecule_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "is_registered",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "register_all_pipelines",
    "uniprot_protein_factory",
]

"""Private non-ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts.gold import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.infrastructure.schemas.silver import (
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

NON_CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        entity_type="compound",
        transformer_class="bioetl.application.pipelines.pubchem.transformer.PubChemCompoundTransformer",
        silver_schema=PUBCHEM_COMPOUND_SCHEMA,
        gold_schema=PubChemCompoundGoldSchema,
        pandera_silver_schema=PubchemMoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        entity_type="protein",
        transformer_class="bioetl.application.pipelines.uniprot.transformer.UniProtProteinTransformer",
        silver_schema=UNIPROT_PROTEIN_SCHEMA,
        gold_schema=UniProtProteinGoldSchema,
        pandera_silver_schema=UniprotTargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_idmapping",
        provider="uniprot",
        entity_type="idmapping",
        transformer_class="bioetl.application.pipelines.uniprot.idmapping_transformer.IDMappingTransformer",
        silver_schema=UNIPROT_ID_MAPPING_SCHEMA,
        gold_schema=UniProtIDMappingGoldSchema,
        pandera_silver_schema=IDMappingSchema,
        data_source_provider="uniprot_idmapping",
    ),
    PipelineFactoryConfig(
        pipeline_name="pubmed_publication",
        provider="pubmed",
        entity_type="publication",
        transformer_class="bioetl.application.pipelines.pubmed.transformer.PubMedPublicationTransformer",
        silver_schema=PUBMED_PUBLICATION_SCHEMA,
        gold_schema=PubMedPublicationGoldSchema,
        pandera_silver_schema=PubMedPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="crossref_publication",
        provider="crossref",
        entity_type="publication",
        transformer_class="bioetl.application.pipelines.crossref.transformer.CrossRefPublicationTransformer",
        silver_schema=CROSSREF_PUBLICATION_SCHEMA,
        gold_schema=CrossRefPublicationGoldSchema,
        pandera_silver_schema=PublicationEnrichedSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="openalex_publication",
        provider="openalex",
        entity_type="publication",
        transformer_class="bioetl.application.pipelines.openalex.transformer.OpenAlexPublicationTransformer",
        silver_schema=OPENALEX_PUBLICATION_SCHEMA,
        gold_schema=OpenAlexPublicationGoldSchema,
        pandera_silver_schema=OpenAlexPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="semanticscholar_publication",
        provider="semanticscholar",
        entity_type="publication",
        transformer_class="bioetl.application.pipelines.semanticscholar.transformer.SemanticScholarPublicationTransformer",
        silver_schema=SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        gold_schema=SemanticScholarPublicationGoldSchema,
        pandera_silver_schema=SemanticScholarPublicationSchema,
    ),
)

__all__ = ["NON_CHEMBL_PIPELINE_CONFIGS"]

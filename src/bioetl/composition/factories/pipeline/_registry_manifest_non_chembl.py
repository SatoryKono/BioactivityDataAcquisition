"""Private non-ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts import gold
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.infrastructure.schemas import silver

NON_CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="pubchem_compound",
        transformer_class="bioetl.application.pipelines.pubchem.transformer.PubChemCompoundTransformer",
        silver_schema=silver.PUBCHEM_COMPOUND_SCHEMA,
        gold_schema=gold.PubChemCompoundGoldSchema,
        pandera_silver_schema=PubchemMoleculeSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="uniprot_protein",
        transformer_class="bioetl.application.pipelines.uniprot.transformer.UniProtProteinTransformer",
        silver_schema=silver.UNIPROT_PROTEIN_SCHEMA,
        gold_schema=gold.UniProtProteinGoldSchema,
        pandera_silver_schema=UniprotTargetSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="uniprot_idmapping",
        transformer_class="bioetl.application.pipelines.uniprot.idmapping_transformer.IDMappingTransformer",
        silver_schema=silver.UNIPROT_ID_MAPPING_SCHEMA,
        gold_schema=gold.UniProtIDMappingGoldSchema,
        pandera_silver_schema=IDMappingSchema,
        data_source_provider="uniprot_idmapping",
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="pubmed_publication",
        transformer_class="bioetl.application.pipelines.pubmed.transformer.PubMedPublicationTransformer",
        silver_schema=silver.PUBMED_PUBLICATION_SCHEMA,
        gold_schema=gold.PubMedPublicationGoldSchema,
        pandera_silver_schema=PubMedPublicationSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="crossref_publication",
        transformer_class="bioetl.application.pipelines.crossref.transformer.CrossRefPublicationTransformer",
        silver_schema=silver.CROSSREF_PUBLICATION_SCHEMA,
        gold_schema=gold.CrossRefPublicationGoldSchema,
        pandera_silver_schema=PublicationEnrichedSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="openalex_publication",
        transformer_class="bioetl.application.pipelines.openalex.transformer.OpenAlexPublicationTransformer",
        silver_schema=silver.OPENALEX_PUBLICATION_SCHEMA,
        gold_schema=gold.OpenAlexPublicationGoldSchema,
        pandera_silver_schema=OpenAlexPublicationSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="semanticscholar_publication",
        transformer_class="bioetl.application.pipelines.semanticscholar.transformer.SemanticScholarPublicationTransformer",
        silver_schema=silver.SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        gold_schema=gold.SemanticScholarPublicationGoldSchema,
        pandera_silver_schema=SemanticScholarPublicationSchema,
    ),
)

__all__ = ["NON_CHEMBL_PIPELINE_CONFIGS"]

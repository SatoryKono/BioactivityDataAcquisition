"""Private ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts import gold
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.subcellular_fraction import (
    SubcellularFractionSchema,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.chembl.target_protein_classification import (
    TargetProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.tissue import TissueSchema
from bioetl.infrastructure.schemas import silver

CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_activity",
        transformer_class="bioetl.application.pipelines.chembl.activity_transformer.ActivityTransformer",
        silver_schema=silver.CHEMBL_ACTIVITY_SCHEMA,
        gold_schema=gold.ChEMBLActivityGoldSchema,
        pandera_silver_schema=ActivitySchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_assay",
        transformer_class="bioetl.application.pipelines.chembl.assay_transformer.AssayTransformer",
        silver_schema=silver.CHEMBL_ASSAY_SCHEMA,
        gold_schema=gold.ChEMBLAssayGoldSchema,
        pandera_silver_schema=AssaySchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_assay_parameters",
        transformer_class="bioetl.application.pipelines.chembl.assay_parameters_transformer.AssayParametersTransformer",
        silver_schema=silver.CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        gold_schema=gold.ChEMBLAssayParametersGoldSchema,
        pandera_silver_schema=AssayParametersSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_cell_line",
        transformer_class="bioetl.application.pipelines.chembl.cell_line_transformer.CellLineTransformer",
        silver_schema=silver.CHEMBL_CELL_LINE_SCHEMA,
        gold_schema=gold.ChEMBLCellLineGoldSchema,
        pandera_silver_schema=CellLineSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_compound_record",
        transformer_class="bioetl.application.pipelines.chembl.compound_record_transformer.CompoundRecordTransformer",
        silver_schema=silver.CHEMBL_COMPOUND_RECORD_SCHEMA,
        gold_schema=gold.ChEMBLCompoundRecordGoldSchema,
        pandera_silver_schema=CompoundRecordSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_publication",
        transformer_class="bioetl.application.pipelines.chembl.publication_transformer.PublicationTransformer",
        silver_schema=silver.CHEMBL_PUBLICATION_SCHEMA,
        gold_schema=gold.ChEMBLPublicationGoldSchema,
        pandera_silver_schema=ChemblPublicationSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_publication_similarity",
        transformer_class="bioetl.application.pipelines.chembl.publication_similarity_transformer.PublicationSimilarityTransformer",
        silver_schema=silver.CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        gold_schema=gold.ChEMBLPublicationSimilarityGoldSchema,
        pandera_silver_schema=PublicationSimilaritySchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_publication_term",
        transformer_class="bioetl.application.pipelines.chembl.publication_term_transformer.PublicationTermTransformer",
        silver_schema=silver.CHEMBL_DOCUMENT_TERM_SCHEMA,
        gold_schema=gold.ChEMBLPublicationTermGoldSchema,
        pandera_silver_schema=PublicationTermSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_molecule",
        transformer_class="bioetl.application.pipelines.chembl.molecule_transformer.MoleculeTransformer",
        silver_schema=silver.CHEMBL_MOLECULE_SCHEMA,
        gold_schema=gold.ChEMBLMoleculeGoldSchema,
        pandera_silver_schema=MoleculeSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_target",
        transformer_class="bioetl.application.pipelines.chembl.target_transformer.TargetTransformer",
        silver_schema=silver.CHEMBL_TARGET_SCHEMA,
        gold_schema=gold.ChEMBLTargetGoldSchema,
        pandera_silver_schema=TargetSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_target_component",
        transformer_class="bioetl.application.pipelines.chembl.target_component_transformer.TargetComponentTransformer",
        silver_schema=silver.CHEMBL_TARGET_COMPONENT_SCHEMA,
        gold_schema=gold.ChEMBLTargetComponentGoldSchema,
        pandera_silver_schema=TargetComponentSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_target_protein_classification",
        transformer_class="bioetl.application.pipelines.chembl.target_protein_classification_transformer.TargetProteinClassificationTransformer",
        silver_schema=silver.CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA,
        gold_schema=gold.ChEMBLTargetProteinClassificationGoldSchema,
        pandera_silver_schema=TargetProteinClassificationSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_protein_class",
        transformer_class="bioetl.application.pipelines.chembl.protein_class_transformer.ProteinClassTransformer",
        silver_schema=silver.CHEMBL_PROTEIN_CLASS_SCHEMA,
        gold_schema=gold.ChEMBLProteinClassGoldSchema,
        pandera_silver_schema=ProteinClassificationSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_tissue",
        transformer_class="bioetl.application.pipelines.chembl.tissue_transformer.TissueTransformer",
        silver_schema=silver.CHEMBL_TISSUE_SCHEMA,
        gold_schema=gold.ChEMBLTissueGoldSchema,
        pandera_silver_schema=TissueSchema,
    ),
    PipelineFactoryConfig.for_pipeline(
        pipeline_name="chembl_subcellular_fraction",
        transformer_class="bioetl.application.pipelines.chembl.subcellular_fraction_transformer.SubcellularFractionTransformer",
        silver_schema=silver.CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        gold_schema=gold.ChEMBLSubcellularFractionGoldSchema,
        pandera_silver_schema=SubcellularFractionSchema,
    ),
)

__all__ = ["CHEMBL_PIPELINE_CONFIGS"]

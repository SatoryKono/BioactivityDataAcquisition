"""Private ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts.gold import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTargetProteinClassificationGoldSchema,
    ChEMBLTissueGoldSchema,
)
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
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
)

CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        transformer_class="bioetl.application.pipelines.chembl.activity_transformer.ActivityTransformer",
        silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        gold_schema=ChEMBLActivityGoldSchema,
        pandera_silver_schema=ActivitySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay",
        provider="chembl",
        entity_type="assay",
        transformer_class="bioetl.application.pipelines.chembl.assay_transformer.AssayTransformer",
        silver_schema=CHEMBL_ASSAY_SCHEMA,
        gold_schema=ChEMBLAssayGoldSchema,
        pandera_silver_schema=AssaySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay_parameters",
        provider="chembl",
        entity_type="assay_parameters",
        transformer_class="bioetl.application.pipelines.chembl.assay_parameters_transformer.AssayParametersTransformer",
        silver_schema=CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        gold_schema=ChEMBLAssayParametersGoldSchema,
        pandera_silver_schema=AssayParametersSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_cell_line",
        provider="chembl",
        entity_type="cell_line",
        transformer_class="bioetl.application.pipelines.chembl.cell_line_transformer.CellLineTransformer",
        silver_schema=CHEMBL_CELL_LINE_SCHEMA,
        gold_schema=ChEMBLCellLineGoldSchema,
        pandera_silver_schema=CellLineSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_compound_record",
        provider="chembl",
        entity_type="compound_record",
        transformer_class="bioetl.application.pipelines.chembl.compound_record_transformer.CompoundRecordTransformer",
        silver_schema=CHEMBL_COMPOUND_RECORD_SCHEMA,
        gold_schema=ChEMBLCompoundRecordGoldSchema,
        pandera_silver_schema=CompoundRecordSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication",
        provider="chembl",
        entity_type="publication",
        transformer_class="bioetl.application.pipelines.chembl.publication_transformer.PublicationTransformer",
        silver_schema=CHEMBL_PUBLICATION_SCHEMA,
        gold_schema=ChEMBLPublicationGoldSchema,
        pandera_silver_schema=ChemblPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_similarity",
        provider="chembl",
        entity_type="publication_similarity",
        transformer_class="bioetl.application.pipelines.chembl.publication_similarity_transformer.PublicationSimilarityTransformer",
        silver_schema=CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        gold_schema=ChEMBLPublicationSimilarityGoldSchema,
        pandera_silver_schema=PublicationSimilaritySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_term",
        provider="chembl",
        entity_type="publication_term",
        transformer_class="bioetl.application.pipelines.chembl.publication_term_transformer.PublicationTermTransformer",
        silver_schema=CHEMBL_DOCUMENT_TERM_SCHEMA,
        gold_schema=ChEMBLPublicationTermGoldSchema,
        pandera_silver_schema=PublicationTermSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_molecule",
        provider="chembl",
        entity_type="molecule",
        transformer_class="bioetl.application.pipelines.chembl.molecule_transformer.MoleculeTransformer",
        silver_schema=CHEMBL_MOLECULE_SCHEMA,
        gold_schema=ChEMBLMoleculeGoldSchema,
        pandera_silver_schema=MoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target",
        provider="chembl",
        entity_type="target",
        transformer_class="bioetl.application.pipelines.chembl.target_transformer.TargetTransformer",
        silver_schema=CHEMBL_TARGET_SCHEMA,
        gold_schema=ChEMBLTargetGoldSchema,
        pandera_silver_schema=TargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target_component",
        provider="chembl",
        entity_type="target_component",
        transformer_class="bioetl.application.pipelines.chembl.target_component_transformer.TargetComponentTransformer",
        silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
        gold_schema=ChEMBLTargetComponentGoldSchema,
        pandera_silver_schema=TargetComponentSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target_protein_classification",
        provider="chembl",
        entity_type="target_protein_classification",
        transformer_class="bioetl.application.pipelines.chembl.target_protein_classification_transformer.TargetProteinClassificationTransformer",
        silver_schema=CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA,
        gold_schema=ChEMBLTargetProteinClassificationGoldSchema,
        pandera_silver_schema=TargetProteinClassificationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_protein_class",
        provider="chembl",
        entity_type="protein_class",
        transformer_class="bioetl.application.pipelines.chembl.protein_class_transformer.ProteinClassTransformer",
        silver_schema=CHEMBL_PROTEIN_CLASS_SCHEMA,
        gold_schema=ChEMBLProteinClassGoldSchema,
        pandera_silver_schema=ProteinClassificationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity_type="tissue",
        transformer_class="bioetl.application.pipelines.chembl.tissue_transformer.TissueTransformer",
        silver_schema=CHEMBL_TISSUE_SCHEMA,
        gold_schema=ChEMBLTissueGoldSchema,
        pandera_silver_schema=TissueSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_subcellular_fraction",
        provider="chembl",
        entity_type="subcellular_fraction",
        transformer_class="bioetl.application.pipelines.chembl.subcellular_fraction_transformer.SubcellularFractionTransformer",
        silver_schema=CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        gold_schema=ChEMBLSubcellularFractionGoldSchema,
        pandera_silver_schema=SubcellularFractionSchema,
    ),
)

__all__ = ["CHEMBL_PIPELINE_CONFIGS"]

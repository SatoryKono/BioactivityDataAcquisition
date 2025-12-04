"""Pipeline schema contracts and registry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineSchemaContract:
    """Описание схем для пайплайна."""

    pipeline_code: str
    schema_out: str
    schema_in: str | None = None
    output_schema: str | None = None

    def get_output_schema(self) -> str:
        """Возвращает схему для записи (fallback на schema_out)."""

        return self.output_schema or self.schema_out


def _default_contract(code: str, entity: str | None) -> PipelineSchemaContract:
    schema_name = entity or code
    return PipelineSchemaContract(
        pipeline_code=code,
        schema_out=schema_name,
        schema_in=schema_name,
        output_schema=schema_name,
    )


PIPELINE_CONTRACTS: dict[str, PipelineSchemaContract] = {
    "activity_chembl": PipelineSchemaContract(
        pipeline_code="activity_chembl",
        schema_out="activity",
        schema_in="activity_input",
        output_schema="activity_output",
    ),
    "assay_chembl": PipelineSchemaContract(
        pipeline_code="assay_chembl",
        schema_out="assay",
        schema_in="assay_input",
        output_schema="assay_output",
    ),
    "document_chembl": PipelineSchemaContract(
        pipeline_code="document_chembl",
        schema_out="document",
        schema_in="document_input",
        output_schema="document_output",
    ),
    "target_chembl": PipelineSchemaContract(
        pipeline_code="target_chembl",
        schema_out="target",
        schema_in="target_input",
        output_schema="target_output",
    ),
    "testitem_chembl": PipelineSchemaContract(
        pipeline_code="testitem_chembl",
        schema_out="testitem",
        schema_in="testitem_input",
        output_schema="testitem_output",
    ),
    "molecule_chembl": PipelineSchemaContract(
        pipeline_code="molecule_chembl",
        schema_out="testitem",
        schema_in="testitem_input",
        output_schema="testitem_output",
    ),
}


def get_pipeline_contract(
    pipeline_code: str, *, default_entity: str | None = None
) -> PipelineSchemaContract:
    """Возвращает контракт схем для пайплайна."""

    if pipeline_code in PIPELINE_CONTRACTS:
        return PIPELINE_CONTRACTS[pipeline_code]
    return _default_contract(pipeline_code, default_entity)

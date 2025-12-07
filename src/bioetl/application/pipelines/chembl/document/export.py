"""Заглушка стадии export для ChEMBL Document."""

from typing import Final

from bioetl.application.pipelines.chembl.stage_metadata import build_stage_descriptor

PROVIDER_NAME: Final[str] = "chembl"
ENTITY_NAME: Final[str] = "document"
PIPELINE_ID: Final[str] = "document_chembl"
STAGE_NAME: Final[str] = "export"


get_stage_descriptor = build_stage_descriptor(
    provider=PROVIDER_NAME,
    entity=ENTITY_NAME,
    pipeline_id=PIPELINE_ID,
    stage=STAGE_NAME,
)


__all__ = ["get_stage_descriptor", "PROVIDER_NAME", "ENTITY_NAME", "PIPELINE_ID", "STAGE_NAME"]


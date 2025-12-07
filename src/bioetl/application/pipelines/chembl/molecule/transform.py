"""Заглушка стадии transform для ChEMBL Molecule."""

from typing import Final

from bioetl.application.pipelines.chembl.stage_metadata import get_stage_metadata

PROVIDER_NAME: Final[str] = "chembl"
ENTITY_NAME: Final[str] = "molecule"
PIPELINE_ID: Final[str] = "molecule_chembl"
STAGE_NAME: Final[str] = "transform"


def get_stage_descriptor() -> dict[str, str]:
    """Возвращает метаданные стадии для инструментов обнаружения пайплайна."""
    return get_stage_metadata(
        provider=PROVIDER_NAME,
        entity=ENTITY_NAME,
        pipeline_id=PIPELINE_ID,
        stage=STAGE_NAME,
    )


__all__ = ["get_stage_descriptor", "PROVIDER_NAME", "ENTITY_NAME", "PIPELINE_ID", "STAGE_NAME"]


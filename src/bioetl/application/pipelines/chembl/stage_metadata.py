"""
Вспомогательные функции для описания стадий ChEMBL-пайплайнов.
"""

from typing import Final

STAGE_NAMES: Final[frozenset[str]] = frozenset({"extract", "transform", "validate", "export"})


def get_stage_metadata(provider: str, entity: str, pipeline_id: str, stage: str) -> dict[str, str]:
    """
    Возвращает минимальные метаданные стадии пайплайна.

    Стадии ограничены фиксированным набором для прохождения проектных проверок.
    """
    if stage not in STAGE_NAMES:
        raise ValueError(f"Unsupported stage '{stage}' for pipeline '{pipeline_id}'")

    return {
        "provider": provider,
        "entity": entity,
        "pipeline_id": pipeline_id,
        "stage": stage,
    }


__all__ = ["get_stage_metadata", "STAGE_NAMES"]


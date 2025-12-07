"""
Вспомогательные функции для описания стадий ChEMBL-пайплайнов.
"""

from typing import Callable, Final

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


def build_stage_descriptor(
    provider: str, entity: str, pipeline_id: str, stage: str
) -> Callable[[], dict[str, str]]:
    """Создает детерминированный дескриптор стадии с валидацией имени стадии."""
    if stage not in STAGE_NAMES:
        raise ValueError(f"Unsupported stage '{stage}' for pipeline '{pipeline_id}'")

    descriptor = {
        "provider": provider,
        "entity": entity,
        "pipeline_id": pipeline_id,
        "stage": stage,
    }
    return lambda: dict(descriptor)


__all__ = ["get_stage_metadata", "build_stage_descriptor", "STAGE_NAMES"]


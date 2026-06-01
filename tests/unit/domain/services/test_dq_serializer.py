"""Тесты сериализации DQ для доменного помощника."""

from __future__ import annotations

import pytest

from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum

from bioetl.domain.behavior.dq_serializer import to_dict


pytestmark = pytest.mark.unit

class SampleStatus(Enum):
    """Тестовое перечисление для проверки Enum."""

    OK = "ok"


@dataclass
class NestedSample:
    """Вложенная датакласс-модель для проверки рекурсии."""

    value: int
    status: SampleStatus


@dataclass
class ContainerSample:
    """Контейнер для проверки коллекций и словарей."""

    created_at: datetime
    nested: NestedSample
    items: list[NestedSample]
    mapping: dict[str, NestedSample]


def test_to_dict_serializes_dataclass_with_nested_values() -> None:
    """Проверяет рекурсивную сериализацию dataclass/Enum/datetime."""
    timestamp = datetime(2024, 1, 1, 12, 30, tzinfo=UTC)
    nested = NestedSample(value=1, status=SampleStatus.OK)
    container = ContainerSample(
        created_at=timestamp,
        nested=nested,
        items=[nested],
        mapping={"first": nested},
    )

    result = to_dict(container)

    assert result == {
        "created_at": "2024-01-01T12:30:00+00:00",
        "nested": {"value": 1, "status": "ok"},
        "items": [{"value": 1, "status": "ok"}],
        "mapping": {"first": {"value": 1, "status": "ok"}},
    }


def test_to_dict_wraps_non_dataclass_value() -> None:
    """Проверяет оборачивание простого значения в словарь."""
    result = to_dict("sample")

    assert result == {"value": "sample"}

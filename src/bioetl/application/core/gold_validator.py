"""Gold layer schema validator.

Отвечает за валидацию записей перед записью в Gold слой (SRP).
Выделен из RecordProcessor для соблюдения принципа единственной ответственности.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import ValidationResult

if TYPE_CHECKING:
    import pandera as pa


class GoldValidator:
    """Валидатор записей для Gold слоя.

    Проверяет записи на соответствие Pandera-схеме перед записью в Gold.
    Если схема не задана, валидация всегда успешна.

    Attributes:
        _schema: Pandera-схема для валидации (опционально).

    """

    def __init__(self, schema: pa.DataFrameSchema | None) -> None:
        """Инициализирует валидатор.

        Args:
            schema: Pandera-схема для валидации. Если None, валидация пропускается.

        """
        self._schema = schema

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Валидирует список записей.

        Args:
            records: Список записей для валидации.

        Returns:
            ValidationResult с результатом валидации.

        """
        if not self._schema or not records:
            return ValidationResult(valid=True)

        import pandas as pd

        df = pd.DataFrame(records)
        try:
            self._schema.validate(df, lazy=True)
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])

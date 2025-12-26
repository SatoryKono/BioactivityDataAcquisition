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
    В strict mode отсутствие схемы приводит к ошибке валидации.

    Attributes:
        _schema: Pandera-схема для валидации (опционально).
        _strict: Если True, отсутствие схемы вызывает ошибку валидации.

    """

    def __init__(
        self, schema: pa.DataFrameSchema | None, *, strict: bool = False
    ) -> None:
        """Инициализирует валидатор.

        Args:
            schema: Pandera-схема для валидации. Если None и strict=False,
                валидация пропускается. Если None и strict=True, валидация
                завершается с ошибкой.
            strict: Если True, требует наличия схемы для валидации.
                По умолчанию False для обратной совместимости.

        """
        self._schema = schema
        self._strict = strict

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Валидирует список записей.

        Args:
            records: Список записей для валидации.

        Returns:
            ValidationResult с результатом валидации.

        """
        if not records:
            return ValidationResult(valid=True)

        if not self._schema:
            if self._strict:
                return ValidationResult(
                    valid=False,
                    errors=["Gold schema is required but not provided"],
                )
            return ValidationResult(valid=True)

        import pandas as pd

        df = pd.DataFrame(records)
        try:
            self._schema.validate(df, lazy=True)
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])

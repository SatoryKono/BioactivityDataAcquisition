# 27 Validator ABC

## Описание

ValidatorABC выполняет проверку записи по схеме и возвращает ValidationResult. Валидация может включать проверку типов, диапазонов значений, обязательности полей, форматов строк, ссылочной целостности. Интерфейс не навязывает конкретную библиотеку валидации, но гарантирует, что валидатор может проверить запись против схемы и вернуть структурированный результат с информацией об ошибках. Валидатор не должен изменять запись, только проверять её соответствие схеме.

## Interface

```python
from typing import Generic, TypeVar

RecordT = TypeVar("RecordT")
SchemaT = TypeVar("SchemaT")

class ValidatorABC(Generic[RecordT, SchemaT]):
    def validate(self, record: RecordT, schema: SchemaT) -> "ValidationResult[RecordT]":
        """Проверить запись по схеме и вернуть результат валидации."""
        raise NotImplementedError
```

## Related Components

- **SchemaProviderABC**: используется для получения схемы
- **DQRuleABC**: может использовать validator как часть правил качества
- **ProgressReporterABC**: может фиксировать результаты валидации


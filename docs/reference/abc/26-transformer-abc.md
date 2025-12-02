# 26 Transformer ABC

## Описание

TransformerABC преобразует одну запись RecordT в нормализованную форму ValidatedRecordT. Трансформация может включать нормализацию полей, приведение типов, вычисление производных значений, обогащение данными из сайд-инпутов. Интерфейс не навязывает конкретную логику трансформации, но гарантирует, что результат является валидной записью, готовой для дальнейшей обработки. Трансформеры могут быть объединены в цепочки для последовательной обработки данных.

## Interface

```python
from typing import Generic, TypeVar

RecordT = TypeVar("RecordT")
ValidatedRecordT = TypeVar("ValidatedRecordT")

class TransformerABC(Generic[RecordT, ValidatedRecordT]):
    def transform(self, record: RecordT) -> ValidatedRecordT:
        """Преобразовать запись в нормализованную форму."""
        raise NotImplementedError
```

## Related Components

- **LookupEnricherABC**: может использоваться для обогащения данных
- **ValidatorABC**: может использоваться после трансформации
- **StageABC**: transformer может быть реализацией стадии трансформации


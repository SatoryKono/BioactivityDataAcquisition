# 09 Lookup Enricher ABC

## Описание

LookupEnricherABC обогащает запись на основе внешнего словаря (side inputs). Он принимает исходную запись и словарь сайд-инпутов, возвращая обогащённую запись. Обогащение может включать добавление новых полей, нормализацию значений, замену идентификаторов на канонические формы. Интерфейс не навязывает конкретную логику обогащения, но гарантирует, что обогащение опирается на предоставленные сайд-инпуты.

## Interface

```python
from typing import Generic, TypeVar, Mapping

RecordT = TypeVar("RecordT")
EnrichedRecordT = TypeVar("EnrichedRecordT")
SideKeyT = TypeVar("SideKeyT")
SideValueT = TypeVar("SideValueT")

class LookupEnricherABC(Generic[RecordT, EnrichedRecordT, SideKeyT, SideValueT]):
    def enrich(
        self, 
        record: RecordT, 
        side_inputs: Mapping[SideKeyT, SideValueT]
    ) -> EnrichedRecordT:
        """Обогатить запись на основе сайд-инпутов."""
        raise NotImplementedError
```

## Related Components

- **SideInputProviderABC**: предоставляет сайд-инпуты для обогащения
- **TransformerABC**: может использовать enricher как часть трансформации


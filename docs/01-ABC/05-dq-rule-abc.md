# 05 DQ Rule ABC

## Описание

DQRuleABC определяет правило контроля качества данных. Правило анализирует набор записей и возвращает итератор проблем качества (DQIssue). Каждое правило фокусируется на конкретном аспекте качества: полнота данных, корректность значений, консистентность между полями, соответствие бизнес-правилам. Правила могут быть применены на разных стадиях пайплайна и агрегированы в итоговый отчёт о качестве данных.

## Interface

```python
from typing import Generic, TypeVar, Iterable

RecordT = TypeVar("RecordT")

class DQRuleABC(Generic[RecordT]):
    def evaluate(self, records: Iterable[RecordT]) -> Iterable["DQIssue"]:
        """Оценить качество записей и вернуть найденные проблемы."""
        raise NotImplementedError
```

## Related Components

- **ProgressReporterABC**: может фиксировать результаты DQ-проверок
- **ValidatorABC**: валидация по схеме может быть частью DQ-правил


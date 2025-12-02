# ChEMBL Pipeline Base Classes

Иерархия базовых классов, специфичных для источника ChEMBL.

## Иерархия наследования

```text
PipelineBase
    └── PipelineRuntimeBase (unified.py)
            └── PipelineBase (unified)
                    └── ChemblPipelineBase
                            └── ChemblCommonPipeline
```

## 1. ChemblPipelineBase

**Модуль:** `src/bioetl/core/pipeline/unified.py`

Расширяет базовый пайплайн функциональностью, специфичной для экосистемы ChEMBL.

### Ключевые возможности
- **Управление релизом**: Автоматически определяет версию релиза ChEMBL (`chembl_release`) через метаданные API.
- **Extraction Service**: Интегрирует `ChemblExtractionService` для унифицированного извлечения данных.
- **Хуки**: Добавляет хуки `pre_transform` и `domain_enrich`.

### Методы

```python
def get_chembl_release(self) -> str:
    """Возвращает текущую версию релиза ChEMBL (например, 'chembl_34')."""

def domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame:
    """Выполняет доменное обогащение данных (стадия transform)."""
```

## 2. ChemblCommonPipeline

**Модуль:** `src/bioetl/pipelines/chembl/common/base.py`

Базовый класс для всех сущностных пайплайнов (Activity, Assay, Target и т.д.). Реализует шаблон "Template Method" для ChEMBL.

### Ответственность
1. **Конфигурация**: Проверяет специфичные параметры (`batch_size`, `max_url_length`).
2. **Дескрипторы**: Создает `ChemblDescriptorFactory` и строит дескриптор выборки.
3. **Валидация**: Подключает `ValidationService` с соответствующей схемой.
4. **QC**: Генерирует стандартные отчеты качества.

### Пример использования

```python
class ChemblActivityPipeline(ChemblCommonPipeline):
    def build_descriptor(self):
        return self.descriptor_factory.create_activity_descriptor(...)
```

## 3. ChemblDocumentPipeline

**Модуль:** `src/bioetl/pipelines/chembl/document/run.py`

Специализированный пайплайн для документов, поддерживающий сложное обогащение.

### Особенности
- **Режимы работы**: `chembl` (только базовые данные) или `all` (с обогащением).
- **External Enrichment**: Цепочка источников: `Cache` → `Semantic Scholar` → `PubMed` → `CrossRef`.
- **Fallback Policy**: Стратегии обработки ошибок обогащения (`ordered`, `best_effort`, `strict`).


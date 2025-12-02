# Common ChEMBL Logic

**Модуль:** `src/bioetl/pipelines/chembl/common/base.py`

`ChemblCommonPipeline` — это родительский класс для всех ChEMBL-пайплайнов, реализующий шаблон "Template Method".

## Функциональность

### 1. Descriptor Factory
Автоматически инициализирует `ChemblDescriptorFactory`, который используется для создания дескрипторов выборки (объектов, описывающих, какие данные нужно извлечь).

### 2. Extraction Service Integration
В методе `extract` делегирует работу сервису `ChemblExtractionService`. Это позволяет не писать код пагинации в каждом пайплайне.

### 3. Config Validation
При старте проверяет специфичные для ChEMBL параметры конфигурации:
- `batch_size`: Размер батча для обработки.
- `max_url_length`: Ограничение длины URL (важно для GET-запросов с фильтрами).

### 4. Standard QC
Реализует стандартные методы генерации отчетов качества, специфичные для табличных данных ChEMBL.

## Жизненный цикл

```python
def run(self, ...):
    self.prepare_run()
    df = self.extract()      # Delegated to ChemblExtractionService
    df = self.transform(df)  # Abstract, implemented by subclasses
    df = self.validate(df)   # Delegated to ValidationService
    self.write(df, ...)      # Delegated to UnifiedOutputWriter
```


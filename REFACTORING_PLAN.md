# План рефакторинга BioETL (Phase 5: Architecture Refinement)

Данный документ описывает детальный план работ по улучшению архитектуры BioETL, сформированный по результатам аудита от февраля 2026 года.

## 1. Усиление типизации и безопасности (High Priority)

**Цель:** Обеспечить явность переопределения методов и реализации протоколов для предотвращения ошибок при рефакторинге базовых классов.

*   [ ] **Добавить зависимость `typing-extensions`**
    *   Убедиться, что зависимость доступна в `pyproject.toml`.
*   [ ] **Применить `@override` в Infrastructure Adapters**
    *   Файлы: `src/bioetl/infrastructure/adapters/**/*.py`
    *   Классы: `ChemblAdapter`, `PubChemClient`, `UniProtClient`
    *   Методы: `fetch`, `health_check`, `aclose` и другие методы протоколов.
*   [ ] **Применить `@override` в Application Pipelines**
    *   Файлы: `src/bioetl/application/pipelines/**/*.py`
    *   Классы: `ChEMBLActivityPipeline`, `PubChemCompoundPipeline`, `UniProtProteinPipeline`
    *   Методы: `transform_bronze_to_silver`, `should_write_gold`.
*   [ ] **Применить `@override` в Storage Writers**
    *   Файлы: `src/bioetl/infrastructure/storage/*.py`
    *   Классы: `BronzeWriter`, `DeltaWriter`, `GoldWriter`

**Критерии готовности:**
*   Все переопределенные методы помечены декоратором.
*   `mypy` проходит проверку без ошибок.

---

## 2. Рефакторинг Composition Root (Medium Priority)

**Цель:** Упростить `bootstrap.py` и выделить ответственность за сборку пайплайна в отдельный компонент.

*   [ ] **Создать `PipelineAssembler`**
    *   Путь: `src/bioetl/composition/assemblers/pipeline_assembler.py`
    *   Функциональность:
        *   Загрузка `PipelineYamlConfig`.
        *   Создание `RuntimeConfig`.
        *   Инициализация/проверка Metrics Server.
        *   Сборка `FilterConfig`.
        *   Делегирование создания раннера фабрике.
*   [ ] **Обновить `bootstrap_pipeline`**
    *   Путь: `src/bioetl/composition/bootstrap.py`
    *   Изменение: Метод должен делегировать всю логику классу `PipelineAssembler`.

**Критерии готовности:**
*   `bootstrap.py` содержит только вызовы `bootstrap_logger`, `bootstrap_tracer` и делегацию в `PipelineAssembler`.
*   Тесты интеграции проходят успешно.

---

## 3. Асинхронные фильтры Gold слоя (Low Priority)

**Цель:** Подготовить архитектуру к сложным сценариям фильтрации, требующим асинхронного I/O.

*   [ ] **Обновить `BasePipeline`**
    *   Путь: `src/bioetl/application/core/base.py`
    *   Изменение: `def should_write_gold(...)` -> `async def should_write_gold(...)`.
*   [ ] **Обновить `RecordProcessor`**
    *   Путь: `src/bioetl/application/core/record_processor.py`
    *   Изменение: Добавить `await` при вызове `should_write_gold`.
*   [ ] **Обновить реализации пайплайнов**
    *   Убедиться, что все наследники `BasePipeline` корректно реализуют новую сигнатуру (даже если реализация остается синхронной по сути).

**Критерии готовности:**
*   Все тесты (`make test`) проходят.
*   Нет предупреждений `RuntimeWarning: coroutine '...' was never awaited`.

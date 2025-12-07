# Refactoring Plan

## 📋 Статус и контекст
- **Текущее состояние**: Приняты новые строгие правила (`docs/project/01-project-rules.md`).
- **Основная цель**: Приведение кодовой базы в соответствие с Hexagonal Architecture + DDD и новыми правилами именования/структуры.
- **Ограничение**: Zero-sum class count (удалять старое при добавлении нового).

## 🏗️ Целевая архитектура (Ports & Adapters)

### Слои
1.  **Domain** (`src/bioetl/domain/`)
    *   `contracts/` (ABCs/Protocols с суффиксами `ABC`/`Protocol`)
    *   `schemas/` (Pandera схемы)
    *   `models/` (Pydantic модели)
2.  **Application** (`src/bioetl/application/`)
    *   `pipelines/<provider>/<entity>/` (Extract -> Transform -> Validate -> Export)
    *   `services/` (Оркестрация)
3.  **Infrastructure** (`src/bioetl/infrastructure/`)
    *   `impl/` (Реализации ABC с суффиксом `Impl`)
    *   `clients/` (UnifiedAPIClient и его наследники)
    *   `logging/` (UnifiedLogger)
4.  **Interfaces** (`src/bioetl/interfaces/`)
    *   `cli/` (Typer commands)

## 📅 План действий

### Фаза 1: Формализация и Правила (Completed/In Progress)
- [x] Обновить `01-project-rules.md` и `.cursor/rules/`.
- [ ] **Audit Naming**: Проверить все классы на соответствие суффиксам (`*Factory`, `*Client`, `*Impl`, `*ABC`).
- [ ] **Audit Files**: Переименовать файлы документации в `kebab-case` с префиксом `NN-`.
- [ ] **Config Check**: Убедиться, что все конфиги в `configs/` имеют Pydantic-модели.

### Фаза 2: Рефакторинг Базовых Компонентов (Core Refactoring)
*Цель: Выделить контракты и убрать жесткие зависимости.*

**Дополнения по отказу от глобального реестра провайдеров**
- Основываться на `configs/providers.yaml`, сохраняя загрузку через Pydantic-схему и динамический импорт фабрик.
- При миграции обновить все `register_<provider>_provider` фабрики, проверить валидность `ProviderId` и описаний, добавить временный fallback на старый механизм.
- Описать подключение новых DI/портовых механизмов к фабрикам без нарушения правил загрузчика (динамический импорт + Pydantic конфиги остаются источником истины).

1.  **Clients Layer**:
    *   Выделить `DataClientABC` в domain.
    *   Реализовать `ChemblDataClientHTTPImpl` через `UnifiedAPIClient`.
    *   Создать фабрику `default_chembl_client()`.
2.  **Pipeline Layer**:
    *   Перенести логику из `PipelineBase` в композицию компонентов: `ExtractorABC`, `TransformerABC`, `LoaderABC`.
    *   Обеспечить, чтобы каждый пайплайн (`application/pipelines/...`) собирался через Factory.

### Фаза 2b: CI/CD и Автоматизация Портов (Enforcement)
*Цель: Защитить декомпозицию реестра и внедрение портов через пайплайн.*

1.  **Lint & Static**:
    *   Запустить `ruff`, `black`, `isort` и `mypy` в отдельном CI-стейдже перед тестами.
    *   Добавить архитектурный тест `tests/architecture/test_layer_dependencies.py` и `import-linter` в тот же стейдж.
2.  **Docs & Ports**:
    *   Включить сборку документации в CI (использовать существующие цели `docs`/`docs-html` как единый entrypoint).
    *   Подвязать автогенерацию ABC/портовой документации (обновление `docs/ABC_INDEX.md` и клиентских индексов, регенерация `abc_registry.yaml`/`abc_impls.yaml`) к doc-целям, чтобы пайплайн падал при рассинхронизации.
3.  **Гейты приоритетов**:
    *   Сделать стейдж блокирующим для задач декомпозиции реестра и rollout портов (порт-имплементации не мёржатся, пока не проходят lint/архитектурные проверки и автогенерация документации).

### Фаза 3: Детерминизм и Валидация (Reliability)
*Цель: Гарантировать бит-в-бит воспроизводимость.*

1.  **Pandera Everywhere**:
    *   Покрыть все `output` датафреймы схемами.
    *   Внедрить `validate_before_write` политику.
2.  **Atomic Writes**:
    *   Внедрить утилиту `atomic_write(path, content)` (temp -> rename).
    *   Добавить генерацию `meta.yaml` (checksums, row_counts) для каждого артефакта.
3.  **Testing**:
    *   Добавить Golden-тесты для всех критических трансформаций.

### Фаза 4: Оптимизация (Performance)
1.  **Vectorization**: Заменить row-by-row `apply` на векторные операции pandas/numpy.
2.  **Parallelism**: Внедрить параллельную обработку батчей там, где это безопасно.

## 🛠️ Примеры реализации (New Style)

### Контракт (Domain)
```python
# src/bioetl/domain/normalization/contracts.py
class NormalizationStrategyABC(ABC):
    @abstractmethod
    def normalize(self, value: Any) -> Any: ...
```

### Реализация (Infrastructure)
```python
# src/bioetl/infrastructure/normalization/impl.py
class ChemblIdNormalizerImpl(NormalizationStrategyABC):
    def normalize(self, value: Any) -> str:
        # implementation
        return normalized_val
```

### Фабрика (Application/Infra)
```python
# src/bioetl/infrastructure/normalization/factories.py
def default_normalizer_factory(dtype: str) -> NormalizationStrategyABC:
    if dtype == "chembl_id":
        return ChemblIdNormalizerImpl()
    # ...
```

## 📉 Технический долг к устранению
- [ ] Удалить жесткие зависимости `requests` из доменного кода.
- [ ] Убрать `print()` и заменить на `UnifiedLogger`.
- [ ] Унифицировать разрозненные конфиги в иерархию Pydantic-моделей.

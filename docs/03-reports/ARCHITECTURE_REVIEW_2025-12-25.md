# Архитектурный Обзор BioETL

**Дата:** 2025-12-25
**Версия документации:** RULES.md v5.4
**Ветка:** `claude/architecture-review-refactor-WL2ox`

---

## 1. Резюме

Проект BioETL демонстрирует **зрелую архитектуру** на основе Ports & Adapters (Hexagonal) с Medallion Architecture для данных. Кодовая база хорошо структурирована с чёткими границами слоёв, строгим Dependency Injection и обширным тестовым покрытием.

**Общий интегральный балл: 7.85 / 10** (Хорошо)

---

## 2. Числовая Оценка по 10 Категориям

### 2.1. Определение Категорий

| # | Категория | Описание | Вес |
|---|-----------|----------|-----|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal, разделение domain/application/infrastructure | 15% |
| 2 | **Модульность и связность** | Cohesion модулей, низкая coupling, единообразие структуры | 12% |
| 3 | **Качество доменной модели** | Rich entities, value objects, инварианты, чистые функции | 10% |
| 4 | **Dependency Injection** | Инверсия зависимостей, Composition Root, отсутствие создания внутри классов | 12% |
| 5 | **Тестирование** | Покрытие, качество тестов, VCR, архитектурные тесты | 12% |
| 6 | **Обработка ошибок** | Классификация, retry, circuit breaker, graceful shutdown | 10% |
| 7 | **Наблюдаемость** | Structured logging, metrics, tracing, DQ monitoring | 8% |
| 8 | **Безопасность** | PII handling, secrets management, input validation | 6% |
| 9 | **Качество документации** | ADR, RULES.md, CLAUDE.md, inline docs | 7% |
| 10 | **Технический долг и сопровождаемость** | Code smells, дублирование, god objects, TODO/FIXME | 8% |

### 2.2. Детальная Оценка

| Категория | Вес | Оценка | Взвешенный | Обоснование |
|-----------|-----|--------|------------|-------------|
| **Архитектура слоёв** | 0.15 | **9** | 1.35 | Чёткое разделение 5 слоёв, матрица импортов соблюдена, архитектурные тесты enforce контракты |
| **Модульность и связность** | 0.12 | **8** | 0.96 | Хорошая структура пакетов, но некоторые god objects (runner.py 475 LOC, record_processor.py 449 LOC) |
| **Качество доменной модели** | 0.10 | **9** | 0.90 | Frozen dataclasses, rich entities с инвариантами, 12 Protocols, чистые трансформации |
| **Dependency Injection** | 0.12 | **9** | 1.08 | Composition Root в bootstrap.py, GenericPipelineFactory, все зависимости инжектируются |
| **Тестирование** | 0.12 | **8.5** | 1.02 | 198+ тестов, VCR покрытие, архитектурные тесты (61+), но integration только 6 тестов |
| **Обработка ошибок** | 0.10 | **8** | 0.80 | Классификация (Critical/Recoverable/DQ), Circuit Breaker, Graceful Shutdown, но ADR-014 нарушения |
| **Наблюдаемость** | 0.08 | **8** | 0.64 | StructLog, Prometheus metrics, OpenTelemetry tracing, DQ anomaly detection |
| **Безопасность** | 0.06 | **7** | 0.42 | Secrets через env vars, PII hashing в Silver, но VCR санитизация требует проверки |
| **Качество документации** | 0.07 | **9** | 0.63 | 15 ADR, RULES.md 817 строк, 139 требований в REQUIREMENTS.md, русская документация |
| **Технический долг** | 0.08 | **6** | 0.48 | Copy-paste в 8 пайплайнах, random.uniform() в HTTP client, datetime.now() в infrastructure |
| **ИТОГО** | 1.00 | — | **7.85** | — |

### 2.3. Интерпретация Интегрального Балла

| Диапазон | Интерпретация |
|----------|---------------|
| 0.0 – 4.9 | Критическое состояние, требуется срочный рефакторинг |
| 5.0 – 6.9 | Удовлетворительно, есть существенные проблемы |
| **7.0 – 7.9** | **Хорошо, есть области для улучшения** ← Текущий балл |
| 8.0 – 8.9 | Очень хорошо, минорные улучшения |
| 9.0 – 10.0 | Отлично, production-ready enterprise |

**Вывод:** Проект находится в хорошем состоянии с чёткой архитектурой. Основные области для улучшения — устранение технического долга (дублирование, god objects) и исправление нарушений ADR-014 (детерминизм).

---

## 3. Анализ Текущей Архитектуры

### 3.1. Соблюдение Слоистой Структуры

```
src/bioetl/
├── domain/          # ✅ ЧИСТО: 30 файлов, Protocol-based Ports, frozen entities
├── application/     # ✅ ЧИСТО: 55 файлов, Use Cases, оркестрация
├── composition/     # ✅ ЧИСТО: 26 файлов, DI Container, Factories
├── infrastructure/  # ⚠️ 3 НАРУШЕНИЯ: 63 файла, Adapters
└── interfaces/      # ✅ ЧИСТО: CLI, Runners
```

**Матрица импортов — СОБЛЮДЕНА:**
- ✅ Domain → только stdlib + internal domain
- ✅ Application → domain + internal application
- ✅ Composition → всё кроме interfaces
- ✅ Infrastructure → domain + internal infrastructure
- ✅ Interfaces → всё

**Архитектурное enforcement:**
- `tests/architecture/test_layer_dependencies.py` — 51 тест
- `import-linter` в CI

### 3.2. Ports & Adapters (Hexagonal)

**12 Protocols (Ports) определены:**

| Port | Методы | Lifecycle | Статус |
|------|--------|-----------|--------|
| `StoragePort` | write_bronze/silver/gold, clear, vacuum | aclose() | ✅ |
| `DataSourcePort` | fetch, provider_name | aclose(), context manager | ✅ |
| `FilterableDataSourcePort` | fetch_filtered | aclose() | ✅ |
| `LockPort` | acquire, release, heartbeat | aclose() | ✅ |
| `CheckpointPort` | save, load, list_all, delete | aclose() | ✅ |
| `QuarantinePort` | write, inspect, get_stats | aclose() | ✅ |
| `TracingPort` | get_tracer | close() | ✅ |
| `MetricsPort` | observe_histogram, increment_counter, set_gauge | close() | ✅ |
| `LoggerPort` | info, warning, error, debug, exception, bind | — | ✅ |
| `DQMonitorPort` | add_metric, check_quality, update_baseline | — | ✅ |
| `GoldValidatorPort` | validate | — | ✅ |
| `InputFilterPort` | load_filter_ids | — | ✅ |

**Все порты:**
- Помечены `@runtime_checkable`
- Экспортированы в `__all__`
- Имеют тесты контрактов

### 3.3. Явность Границ Модулей

**Сильные стороны:**
- Facade pattern: `from bioetl.domain.ports import ...`
- Публичный API определён через `__all__`
- Подпакеты (ports/, entities/, exceptions/) организованы логично

**Проблемы:**
- `PipelineRunner` (475 LOC) — смешивает health checks, vacuum, DQ monitoring
- `RecordProcessor` (449 LOC) — смешивает batching, transformation, writes

### 3.4. Единообразие Соглашений

**Структура пакетов — КОНСИСТЕНТНА:**
```
src/bioetl/{layer}/
├── __init__.py          # Facade exports
├── {component}.py       # Main logic
└── {subpackage}/        # Organized submodules
```

**Именование — КОНСИСТЕНТНО:**
- Adapters: `{Provider}Adapter` (ChemblAdapter, PubChemAdapter)
- Pipelines: `{Provider}{Entity}Pipeline`
- Transformers: `{Entity}Transformer`
- Factories: `{Component}Factory`

---

## 4. Выявленные Проблемы

### 4.1. Критические (Блокеры)

| ID | Проблема | Файл | Нарушение |
|----|----------|------|-----------|
| **P-001** | `random.uniform()` в retry jitter | `infrastructure/adapters/http/client.py:72` | ADR-014 (детерминизм) |
| **P-002** | `datetime.now()` в infrastructure | `infrastructure/adapters/chembl/client.py:449` | ADR-014 (timestamps из application) |
| **P-003** | Приватный доступ `_client` | `infrastructure/adapters/pubmed/pubmed_client.py:267-273` | Инкапсуляция |

### 4.2. Высокий Приоритет (Tech Debt)

| ID | Проблема | Описание | Файлы |
|----|----------|----------|-------|
| **P-004** | Copy-paste в пайплайнах | 8-9 идентичных конструкторов с fallback трансформером | `application/pipelines/chembl/*.py`, `pubchem/`, `uniprot/`, `pubmed/` |
| **P-005** | God Object: PipelineRunner | 475 LOC, смешивает 5+ ответственностей | `application/core/runner.py` |
| **P-006** | God Object: RecordProcessor | 449 LOC, смешивает batching + transform + write | `application/core/record_processor.py` |

### 4.3. Средний Приоритет

| ID | Проблема | Описание |
|----|----------|----------|
| **P-007** | PubMed extractors дублирование | 5 extractors с похожей структурой без базового класса |
| **P-008** | Малое количество integration тестов | Только 6 integration тестов (может быть недостаточно) |
| **P-009** | Смешанный язык комментариев | Русский + английский в разных частях кода |

### 4.4. Низкий Приоритет

| ID | Проблема | Описание |
|----|----------|----------|
| **P-010** | BaseServicesFactory — статический класс | Менее консистентно с другими фабриками |
| **P-011** | DataSourceRegistry vs ProviderRegistry | Потенциальная рассинхронизация |

---

## 5. Детальный План Рефакторинга

### 5.1. Приоритет 1: Исправление ADR-014 Нарушений

#### Шаг 1.1: Устранить random.uniform() в HTTP Client

**Цель:** Обеспечить детерминизм retry logic для воспроизводимости

**Изменения:**
```python
# infrastructure/adapters/http/client.py

# БЫЛО (line 72):
delay += random.uniform(-jitter_range, jitter_range)

# СТАНЕТ:
if self.deterministic:
    hash_input = f"{attempt}:{url}:{self.jitter_seed}"
    jitter_factor = (hash(hash_input) % 1000) / 1000.0
    delay += jitter_factor * jitter_range
else:
    delay += random.uniform(-jitter_range, jitter_range)
```

**Файлы:**
- `src/bioetl/infrastructure/adapters/http/client.py`

**Риски:**
- Изменение поведения в существующих тестах
- **Митигация:** Запустить полный тест suite после изменения

**Критерий готовности:**
- [ ] `test_no_random_in_writers` проходит
- [ ] Все integration тесты проходят
- [ ] `deterministic=True` по умолчанию в bootstrap

---

#### Шаг 1.2: Устранить datetime.now() в ChemblAdapter

**Цель:** Timestamps должны инжектироваться из application слоя

**Изменения:**
```python
# infrastructure/adapters/chembl/client.py

# БЫЛО (line 449):
self._last_health_check = datetime.now()

# СТАНЕТ:
# Удалить если не используется, или
# Передавать timestamp как параметр health_check(timestamp: datetime)
```

**Риски:**
- Потенциальное breaking change если `_last_health_check` используется
- **Митигация:** Grep по usage перед удалением

**Критерий готовности:**
- [ ] `test_no_datetime_now_in_infrastructure` проходит
- [ ] Health check работает корректно

---

#### Шаг 1.3: Исправить инкапсуляцию в PubMedAdapter

**Цель:** Не обращаться к приватным атрибутам UnifiedHTTPClient

**Изменения:**
```python
# infrastructure/adapters/pubmed/pubmed_client.py

# БЫЛО:
async def aclose(self) -> None:
    if self.http_client and hasattr(self.http_client, "_client"):
        await self.http_client._client.aclose()

# СТАНЕТ:
async def aclose(self) -> None:
    if self.http_client:
        await self.http_client.__aexit__(None, None, None)
```

**Критерий готовности:**
- [ ] aclose() корректно освобождает ресурсы
- [ ] Нет доступа к приватным атрибутам

---

### 5.2. Приоритет 2: Устранение Дублирования в Пайплайнах

#### Шаг 2.1: Создать TransformerRegistry

**Цель:** Убрать copy-paste конструкторов с fallback трансформером

**Текущая проблема:**
```python
# Повторяется в 8 файлах:
def __init__(self, config, runtime, services, run_id, transformer=None):
    if transformer is None:
        from ...transformer import XxxTransformer
        transformer = XxxTransformer(provider=config.provider)
    super().__init__(...)
```

**Решение:**
```python
# composition/factories/transformer_registry.py

class TransformerRegistry:
    _transformers: dict[str, type[BaseTransformer]] = {}

    @classmethod
    def register(cls, pipeline_name: str, transformer_class: type) -> None:
        cls._transformers[pipeline_name] = transformer_class

    @classmethod
    def get(cls, pipeline_name: str, provider: str) -> BaseTransformer:
        transformer_class = cls._transformers[pipeline_name]
        return transformer_class(provider=provider)

# Регистрация:
TransformerRegistry.register("chembl_activity", ActivityTransformer)
TransformerRegistry.register("chembl_assay", AssayTransformer)
# ...
```

**Изменения в пайплайнах:**
```python
# application/pipelines/chembl/activity.py

class ChEMBLActivityPipeline(BasePipeline):
    # Убрать __init__ полностью — использовать родительский
    pass
```

**Файлы:**
- Создать: `src/bioetl/composition/factories/transformer_registry.py`
- Изменить: 8-9 файлов пайплайнов

**Критерий готовности:**
- [ ] Все пайплайны работают через registry
- [ ] Нет дублирования конструкторов
- [ ] Тесты пайплайнов проходят

---

### 5.3. Приоритет 3: Разделение God Objects

#### Шаг 3.1: Извлечь HealthCheckOrchestrator из PipelineRunner

**Цель:** SRP — отделить логику health checks

**Новый класс:**
```python
# application/core/health_orchestrator.py

class HealthCheckOrchestrator:
    def __init__(self, services: PipelineServices, config: PipelineConfig):
        self.services = services
        self.config = config

    async def validate_infrastructure(self) -> HealthReport:
        """Pre-flight health checks для всех компонентов."""
        ...

    async def check_provider_health(self) -> HealthStatus:
        """Проверка здоровья провайдера данных."""
        ...
```

**Изменения в PipelineRunner:**
```python
# БЫЛО:
async def _validate_infrastructure(self) -> None:
    # 50+ строк логики

# СТАНЕТ:
async def _validate_infrastructure(self) -> None:
    orchestrator = HealthCheckOrchestrator(self.services, self.config)
    report = await orchestrator.validate_infrastructure()
    if not report.is_healthy:
        raise InfrastructureError(...)
```

**Файлы:**
- Создать: `src/bioetl/application/core/health_orchestrator.py`
- Изменить: `src/bioetl/application/core/runner.py`

**Критерий готовности:**
- [ ] `runner.py` < 350 LOC
- [ ] HealthCheckOrchestrator полностью покрыт тестами
- [ ] Все существующие тесты проходят

---

#### Шаг 3.2: Извлечь VacuumOrchestrator из PipelineRunner

**Цель:** SRP — отделить логику VACUUM

**Новый класс:**
```python
# application/core/vacuum_orchestrator.py

class VacuumOrchestrator:
    def __init__(self, lifecycle_service: MedallionLifecycleService):
        self.lifecycle = lifecycle_service

    async def run_if_enabled(
        self,
        runtime: RuntimeConfig,
        tables: list[str]
    ) -> VacuumResult:
        """Запуск VACUUM если включен в runtime config."""
        ...
```

**Критерий готовности:**
- [ ] VACUUM логика изолирована
- [ ] Тесты покрывают все сценарии

---

#### Шаг 3.3: Разделить RecordProcessor на BatchWriter + BatchTransformer

**Цель:** SRP — разделить трансформацию и запись

**Новые классы:**
```python
# application/core/batch_transformer.py
class BatchTransformer:
    """Трансформация Bronze → Silver."""
    async def transform_batch(self, records: list[BronzeRecord]) -> TransformResult:
        ...

# application/core/batch_writer.py
class BatchWriter:
    """Запись в Bronze/Silver/Gold слои."""
    async def write_bronze(self, records: list[BronzeRecord]) -> None: ...
    async def write_silver(self, records: list[SilverRecord]) -> None: ...
    async def write_gold(self, records: list[dict]) -> None: ...
```

**Критерий готовности:**
- [ ] `RecordProcessor` < 200 LOC (оркестрирует BatchTransformer + BatchWriter)
- [ ] Тесты покрывают обе новые компоненты

---

### 5.4. Приоритет 4: Унификация PubMed Extractors

#### Шаг 4.1: Создать BaseFieldExtractor

**Цель:** DRY — убрать дублирование в 5 extractors

**Текущая структура:**
```
pubmed/extractors/
├── author.py       # extract_authors(), normalize_author()
├── date.py         # extract_date(), normalize_date()
├── abstract.py     # extract_abstract()
├── identifier.py   # extract_identifiers()
└── classification.py
```

**Решение:**
```python
# application/pipelines/pubmed/extractors/base.py

class BaseFieldExtractor(ABC):
    @abstractmethod
    def extract(self, article_element: Element) -> Any:
        """Извлечь данные из XML элемента."""
        ...

    @abstractmethod
    def normalize(self, raw_value: Any) -> Any:
        """Нормализовать извлечённое значение."""
        ...

    def process(self, article_element: Element) -> Any:
        """Template method: extract → normalize."""
        raw = self.extract(article_element)
        return self.normalize(raw) if raw else None
```

**Критерий готовности:**
- [ ] Все extractors наследуют BaseFieldExtractor
- [ ] Нет дублирования структуры

---

### 5.5. Приоритет 5: Увеличение Integration Тестов

#### Шаг 5.1: Добавить Integration тесты для edge cases

**Цель:** Увеличить покрытие integration слоя

**Новые тесты:**
- [ ] Rate limiting behavior (429 response handling)
- [ ] Circuit breaker trip and recovery
- [ ] Graceful shutdown mid-batch
- [ ] Checkpoint resume after failure
- [ ] Schema drift detection

**Критерий готовности:**
- [ ] Integration тестов >= 15
- [ ] Покрыты все Recoverable error сценарии

---

## 6. Матрица Рисков Рефакторинга

| Шаг | Риск | Вероятность | Влияние | Митигация |
|-----|------|-------------|---------|-----------|
| 1.1 | Изменение поведения retry | Средняя | Высокое | Полный тест suite + canary release |
| 1.2 | Breaking change health_check | Низкая | Среднее | Grep usage перед удалением |
| 2.1 | Регрессия в pipeline creation | Средняя | Высокое | Сохранить old constructors deprecated |
| 3.1-3.3 | Нарушение orchestration | Средняя | Высокое | Инкрементальные изменения + тесты |
| 4.1 | Изменение XML parsing | Низкая | Низкое | Unit тесты extractors |
| 5.1 | Flaky тесты | Средняя | Низкое | VCR кассеты для новых тестов |

---

## 7. Метрики и Контроль Качества

### 7.1. Текущие Метрики

| Метрика | Текущее | Целевое | Проверка |
|---------|---------|---------|----------|
| Test coverage | ~80% | ≥80% | `make test --cov` |
| Arch tests passing | 61/61 | 61/61 | `make arch-test` |
| Max file LOC | 615 (storage_factory) | ≤400 | Custom linter |
| Pipeline duplication | 8 файлов | 0 | Manual review |
| ADR-014 violations | 3 | 0 | Arch tests |

### 7.2. Новые Метрики (рекомендуемые)

| Метрика | Цель | Инструмент |
|---------|------|------------|
| Cyclomatic complexity | ≤10 per function | `radon cc` |
| Maintainability index | ≥65 | `radon mi` |
| Code duplication | ≤3% | `pylint --duplicate-code` |
| Import depth | ≤4 levels | Custom |

### 7.3. Связь Метрик с Интегральным Баллом

**Прогноз изменения балла после рефакторинга:**

| Категория | До | После | Δ |
|-----------|-----|-------|---|
| Технический долг | 6.0 | 8.5 | +2.5 |
| Модульность | 8.0 | 9.0 | +1.0 |
| Тестирование | 8.5 | 9.0 | +0.5 |

**Ожидаемый интегральный балл после рефакторинга:**
- Текущий: **7.85**
- После Priority 1-3: **~8.3**
- После Priority 1-5: **~8.6**

---

## 8. Хронология Рефакторинга

| Этап | Шаги | Критерий завершения |
|------|------|---------------------|
| **Этап 1** | 1.1, 1.2, 1.3 | ADR-014 полностью соблюдён |
| **Этап 2** | 2.1 | Нет дублирования в пайплайнах |
| **Этап 3** | 3.1, 3.2, 3.3 | runner.py < 300 LOC, record_processor.py < 200 LOC |
| **Этап 4** | 4.1 | PubMed extractors унифицированы |
| **Этап 5** | 5.1 | Integration тестов >= 15 |

---

## 9. Заключение

Проект BioETL демонстрирует **качественную архитектуру** с чёткими границами слоёв, строгим DI и хорошим тестовым покрытием. Основные области для улучшения:

1. **Критические:** Исправить 3 нарушения ADR-014 (детерминизм)
2. **Высокий приоритет:** Устранить copy-paste в пайплайнах и разбить god objects
3. **Средний приоритет:** Унификация extractors и увеличение integration тестов

После выполнения плана рефакторинга ожидается повышение интегрального балла с **7.85 до ~8.6**, что переведёт проект в категорию "Очень хорошо".

---

*Документ подготовлен на основе анализа кодовой базы от 2025-12-25*
*Версия RULES.md: 5.4*

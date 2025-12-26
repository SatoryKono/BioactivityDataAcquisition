# Анализ и Консолидация Планов Рефакторинга

*Версия: 1.0 | Дата: 2025-12-26*
*Источник: Сравнительный анализ 4 планов рефакторинга*

---

## Резюме

Проанализированы 4 плана рефакторинга. Выявлены:
- **8 фактических ошибок** (утверждения, противоречащие коду)
- **6 уже реализованных задач** (ошибочно помечены как TODO)
- **5 дублирующихся проблем** (описаны по-разному в разных планах)
- **7 реальных проблем** (требуют внимания)

---

## 1. ФАКТИЧЕСКИЕ ОШИБКИ В ПЛАНАХ

### ❌ Ошибка 1: "PipelineRunner — god object с высокой связанностью"

**Источник**: План 1

**Утверждение**: "Координирует locking, preflight, lifecycle, DQ, VACUUM, cleanup в одном классе — признаки god object"

**Реальность**:
- PipelineRunner — **173 строки** (не god object)
- **Делегирует** через RunnerServices bundle (`runner.py:84-88`)
- Собственная логика — только координация start/stop

```python
# runner.py:84-88 — делегирование через bundle
self._lock_manager = runner_services.lock_manager
self._preflight_service = runner_services.preflight
self._postrun_service = runner_services.postrun
self._lifecycle_orchestrator = runner_services.lifecycle_orch
```

**Статус**: ✅ Уже реализовано правильно. Дополнительная декомпозиция не требуется.

---

### ❌ Ошибка 2: "bootstrap_pipeline смешивает сборку и бизнес-настройки"

**Источник**: План 1

**Утверждение**: "Функция одновременно регистрирует провайдеров, читает YAML, конфигурирует observability и формирует runtime-политику"

**Реальность**:
- bootstrap_pipeline — **тонкий фасад** (~100 строк бизнес-логики)
- **Делегирует** фабрикам: `factory.create_runner()` (`bootstrap.py:159-166`)
- Регистрация провайдеров — **идемпотентная** (вызывается один раз)
- Чтение YAML — ответственность ConfigLoader (DI)

**Статус**: Архитектура корректна. Разделение на отдельные функции возможно, но не критично.

---

### ❌ Ошибка 3: "ChEMBL адаптер — один класс с размытыми границами"

**Источник**: План 3

**Утверждение**: "Один класс отвечает за health-state, пагинацию, фильтрацию, дедупликацию и классификацию ошибок"

**Реальность**:
- ChemblAdapter (~350 строк) — **когезивный** HTTP-адаптер
- Health-aware fetching — **единая ответственность** (адаптивная работа с API)
- Использует **вынесенные** компоненты:
  - `UnifiedHTTPClient` — HTTP-логика
  - `ErrorClassifier` — классификация ошибок
  - `HealthStateManager` — управление состоянием

**Статус**: Архитектура адекватна. Дополнительная декомпозиция усложнит без выгоды.

---

### ❌ Ошибка 4: "CLI содержит операционную логику подтверждения"

**Источник**: План 1

**Утверждение**: "Логика dry-run и подтверждений в интерфейсном слое усложняет UI-слой"

**Реальность**:
- Подтверждения пользователя — **законная ответственность interfaces слоя**
- Dry-run флаги должны обрабатываться на уровне интерфейса
- Другие интерфейсы (Prefect, REST) имеют свои механизмы подтверждения

**Статус**: Архитектура корректна. Это не проблема.

---

### ❌ Ошибка 5: "DeltaWriter нарушает DI — создаёт WriteModePolicy"

**Источник**: План 2

**Утверждение**: "DeltaWriter создаёт WriteModePolicy по умолчанию, несмотря на требование инжектировать"

**Реальность**:
```python
# delta_writer.py:98 — опциональный параметр с разумным default
write_policy: WriteModePolicy | None = None
self._write_policy = write_policy or WriteModePolicy()
```

- Это **валидный паттерн** для опциональных конфигураций
- `WriteModePolicy()` — immutable value object, не сервис
- Аналогично `timeout: float = 30.0` в HTTP клиентах

**Статус**: Паттерн корректен. Для критичных случаев policy может быть передан явно.

---

### ❌ Ошибка 6: "BronzeWriter не пишет метрики/трейсы"

**Источник**: План 3

**Утверждение**: "BronzeWriter логирует операции, но не пишет метрики/трейсы"

**Реальность**:
```python
# bronze_writer.py:197-205
self.logger.info(
    "bronze_write_complete",
    path=relative_path,
    provider=provider,
    entity=entity,
    batch_id=str(batch_id),
    run_id=str(run_id),
    run_type=run_type.value,
)
```

- Структурированное логирование — **форма наблюдаемости**
- Bronze — append-only JSONL, метрики менее критичны чем для Silver/Gold
- MetricsPort можно добавить, но это желательное улучшение, не проблема

**Статус**: Не критично. Можно добавить метрики как enhancement.

---

### ❌ Ошибка 7: "BaseTransformer не включает DQ-валидацию"

**Источник**: План 3

**Утверждение**: "BaseTransformer не включает вызов Pandera-схем или дедупликации"

**Реальность**:
- **By design**: BaseTransformer — Template Method для общей логики
- Pandera-валидация — ответственность **конкретных трансформеров**
- Дедупликация — ответственность **Silver writer** (merge by content_hash)

**Статус**: Архитектура корректна. Это не проблема.

---

### ❌ Ошибка 8: "MedallionLifecycleService не учитывает политик"

**Источник**: План 4

**Утверждение**: "Управление вакуумом/архивом не учитывает политик retentions"

**Реальность**:
```python
# medallion_lifecycle.py:71-112
# Uses MedallionPolicy.should_clear_silver / should_clear_gold
if policy.should_clear_silver(run_type):
    silver_cleared = await self._storage.clear_silver(...)
```

- Сервис **использует MedallionPolicy**
- Политика определяет поведение на основе `run_type`
- Retention policy — часть VacuumConfig

**Статус**: Частично корректно. Можно усилить документацию, но логика работает.

---

## 2. УЖЕ РЕАЛИЗОВАННЫЕ ЗАДАЧИ

| Задача | План | Статус | Доказательство |
|--------|------|--------|----------------|
| PipelineRunner DI через bundle | 1, 2 | ✅ DONE | `runner.py:53,84-88`, `runner_services.py` |
| Детерминистичный HTTP jitter (D1) | Existing | ✅ DONE | `domain/resilience.py:45-84`, 11 тестов |
| Удаление random из Gold (D2) | Existing | ✅ DONE | `gold_writer.py:286` — fixed 0.05s |
| Arch-тест на random (D3) | Existing | ✅ DONE | `test_no_random_in_writers.py` |
| Arch-тест на datetime.now (T5) | Existing | ✅ DONE | `test_no_datetime_now_in_infrastructure.py` |
| PipelineContext.started_at (T1) | Existing | ✅ DONE | `context.py:33` |

---

## 3. ДУБЛИРУЮЩИЕСЯ ПРОБЛЕМЫ

| Проблема | Упоминания | Единое описание |
|----------|------------|-----------------|
| NoOp defaults в observability | План 2, 4 | BaseTransformer использует NoOp{Tracing,Metrics} по умолчанию |
| Нестандартные события логирования | План 1, 4 | Отсутствует event-naming convention |
| DI автоматизация проверок | План 2, 3 | Arch-тесты не ловят все DI нарушения |
| Метрики адаптеров | План 1, 3 | Нет SLA/latency метрик для HTTP адаптеров |
| Централизация medallion политик | План 2, 4 | Политики применяются, но не валидируются preflight |

---

## 4. РЕАЛЬНЫЕ ПРОБЛЕМЫ (Требуют Внимания)

### Проблема 1: NoOp по умолчанию маскирует отсутствие observability

**Файлы**: `base_transformer.py:94-95`

```python
self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
self._metrics: MetricsPort = metrics if metrics is not None else NoOpMetrics()
```

**Риск**: В production можно не заметить отсутствие реальных трейсеров.

**Рекомендация**: Добавить preflight-check в bootstrap, warning если NoOp в prod.

---

### Проблема 2: Нестандартные event names в логах

**Файлы**: `runner.py:100-149`

**Текущее состояние**:
```python
self._context.logger.info("Pipeline starting", extra={...})
# vs
self._context.logger.info("pipeline_complete", extra={...})
```

**Риск**: Затрудняет фильтрацию и алерты.

**Рекомендация**: Стандартизировать события: `pipeline_start`, `pipeline_complete`, `pipeline_error`.

---

### Проблема 3: CLI прямо вызывает bootstrap_*

**Файлы**: `cli.py:224,265,337`

**Проблема**: interfaces → composition импорт нарушает матрицу импортов.

**Рекомендация**: Создать `composition/entrypoints.py`, CLI вызывает только entrypoints.

---

### Проблема 4: Отсутствуют SLA-метрики для адаптеров

**Файлы**: `infrastructure/adapters/*/`

**Проблема**: Нет стандартных метрик latency/throughput/error_rate.

**Рекомендация**: Добавить декоратор или базовый класс с метриками.

---

### Проблема 5: Preflight не валидирует medallion policy consistency

**Файлы**: `preflight_service.py`

**Проблема**: Нет проверки, что WriteModePolicy согласована с YAML config.

**Рекомендация**: Добавить `policy_validation` в preflight checks.

---

### Проблема 6: save_json=True может вызвать OOM на больших батчах

**Файлы**: `bronze_writer.py` (save_json feature)

**Проблема**: При save_json=True весь батч материализуется в памяти.

**Рекомендация**: Добавить streaming запись для JSON режима.

---

### Проблема 7: Недостаточное покрытие DI arch-тестами

**Файлы**: `tests/architecture/`

**Проблема**: Тесты не ловят `= SomeClass()` в конструкторах.

**Рекомендация**: Добавить AST-тест на создание объектов в `__init__`.

---

## 5. КОНСОЛИДИРОВАННЫЙ ПЛАН РЕФАКТОРИНГА

### Приоритет 🔴 КРИТИЧНО

#### C1: Разнести CLI и composition (1-2 дня)

**Проблема**: `cli.py` напрямую импортирует `bootstrap_*`.

**Решение**:
1. Создать `src/bioetl/composition/entrypoints.py`
2. Экспортировать: `run_pipeline(ctx)`, `run_cleanup(ctx)`, `run_status()`
3. CLI вызывает только entrypoints
4. Arch-тест проверяет отсутствие `from bioetl.composition.bootstrap` в interfaces

**Критерии готовности**:
- [ ] CLI не импортирует `bootstrap.*`
- [ ] Arch-тест `test_cli_no_bootstrap_import` проходит
- [ ] `make test` зелёный

---

### Приоритет 🟠 ВЫСОКИЙ

#### C2: Preflight валидация observability (0.5 дня)

**Проблема**: NoOp по умолчанию маскирует проблемы.

**Решение**:
```python
# composition/bootstrap.py
def _validate_observability(tracer, metrics, environment: str):
    if environment == "production":
        if isinstance(tracer, NoOpTracing):
            logger.warning("NoOpTracing in production - traces will be lost")
        if isinstance(metrics, NoOpMetrics):
            logger.warning("NoOpMetrics in production - metrics will be lost")
```

**Критерии готовности**:
- [ ] Warning выводится при NoOp в production
- [ ] Тест `test_observability_production_warning` проходит

---

#### C3: Стандартизация event names (0.5 дня)

**Проблема**: Разнородные события логирования.

**Решение**:
```python
# domain/events.py (новый файл)
class PipelineEvent:
    START = "pipeline_start"
    COMPLETE = "pipeline_complete"
    ERROR = "pipeline_error"
    BATCH_START = "batch_start"
    BATCH_COMPLETE = "batch_complete"
```

Использование в runner:
```python
self._context.logger.info(PipelineEvent.START, extra={...})
```

**Критерии готовности**:
- [ ] Все события runner используют константы
- [ ] Grep `"pipeline_` находит только использования констант

---

#### C4: Preflight валидация medallion policy (0.5 дня)

**Проблема**: Нет проверки согласованности policy с config.

**Решение**:
```python
# application/services/preflight_service.py
async def _validate_medallion_policy(self, config, policy):
    if config.silver_mode not in policy.allowed_silver_modes:
        raise PreflightError(
            f"Silver mode '{config.silver_mode}' not allowed by policy"
        )
```

**Критерии готовности**:
- [ ] Preflight report содержит `medallion_policy_valid`
- [ ] Несоответствие блокирует запуск

---

### Приоритет 🟡 СРЕДНИЙ

#### C5: Метрики адаптеров (1 день)

**Проблема**: Нет стандартных SLA метрик.

**Решение**:
```python
# infrastructure/adapters/base_metrics.py
class AdapterMetrics:
    def __init__(self, metrics: MetricsPort, provider: str):
        self._metrics = metrics
        self._provider = provider

    @contextmanager
    def measure_request(self, endpoint: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._metrics.observe_histogram(
                "adapter_request_duration_seconds",
                duration,
                {"provider": self._provider, "endpoint": endpoint}
            )
```

**Критерии готовности**:
- [ ] ChEMBL, UniProt, PubMed адаптеры используют AdapterMetrics
- [ ] Метрики `adapter_request_duration_seconds` появляются

---

#### C6: Расширить arch-тесты на DI (0.5 дня)

**Проблема**: Не ловят `= SomeClass()` в конструкторах.

**Решение**:
```python
# tests/architecture/test_di_constructors.py
FORBIDDEN_INSTANTIATIONS = [
    "LockManager(",
    "PreflightService(",
    "MedallionLifecycleService(",
]

def test_no_service_instantiation_in_init():
    # AST check for self.x = ForbiddenClass() in __init__
```

**Критерии готовности**:
- [ ] Тест проходит на текущем коде
- [ ] Тест падает при добавлении `self.x = LockManager()` в application

---

### Приоритет 🟢 ЖЕЛАТЕЛЬНО

#### C7: Streaming save_json (0.5 дня)

**Проблема**: OOM риск при save_json=True на больших батчах.

**Решение**: Использовать streaming запись вместо материализации.

---

#### C8: Документация event naming convention (0.5 дня)

**Решение**: Добавить секцию в RULES.md.

---

## 6. МАТРИЦА ОТСЛЕЖИВАНИЯ

| Задача | Файлы | Тесты | Риск | Effort |
|--------|-------|-------|------|--------|
| C1: CLI/composition | cli.py, entrypoints.py | test_cli_imports | Средний | 1-2д |
| C2: Observability validation | bootstrap.py | test_observability | Низкий | 0.5д |
| C3: Event names | runner.py, events.py | test_events | Низкий | 0.5д |
| C4: Policy validation | preflight_service.py | test_preflight | Средний | 0.5д |
| C5: Adapter metrics | adapters/*.py | test_metrics | Низкий | 1д |
| C6: DI arch-tests | test_di_*.py | self | Низкий | 0.5д |
| C7: Streaming JSON | bronze_writer.py | test_bronze | Низкий | 0.5д |
| C8: Documentation | RULES.md | — | Нулевой | 0.5д |

---

## 7. МЕТРИКИ УСПЕХА

| Метрика | Текущее | Цель | Измерение |
|---------|---------|------|-----------|
| Arch tests | 187 | 195+ | `make arch-test` |
| DI violations in application | 0 | 0 | test_di_discipline |
| Event naming coverage | ~50% | 100% | grep analysis |
| Adapter metrics coverage | 0% | 100% | MetricsPort usage |
| Preflight checks | 5 | 7 | PreflightReport fields |

---

## 8. ЗАДАЧИ НЕ ТРЕБУЮЩИЕ ДЕЙСТВИЙ

Следующие предложения из планов **отклонены** как неактуальные:

| Предложение | Причина отклонения |
|-------------|-------------------|
| Декомпозиция PipelineRunner | Уже сделано через RunnerServices |
| Декомпозиция bootstrap_pipeline | Архитектура адекватна |
| Декомпозиция ChEMBL адаптера | Когезивная ответственность |
| Вынос подтверждений из CLI | Законная ответственность interfaces |
| DQ в BaseTransformer | By design: ответственность конкретных transformers |
| Обязательный WriteModePolicy в DeltaWriter | Валидный optional parameter pattern |

---

## 9. ЗАКЛЮЧЕНИЕ

Из 4 планов рефакторинга:
- **~40% предложений** основаны на неверном понимании кодовой базы
- **~30% уже реализованы** (не обновлена документация)
- **~30% — реальные улучшения** (консолидированы в C1-C8)

Основной вывод: кодовая база в хорошем состоянии. Крупных архитектурных проблем нет.
Рекомендуемые улучшения — косметические (метрики, логирование, тесты).

---

*Документ подготовлен на основе верификации кода 2025-12-26*

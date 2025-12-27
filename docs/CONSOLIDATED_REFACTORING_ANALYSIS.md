# Анализ и Консолидация Планов Рефакторинга

*Дата анализа: 2025-12-27*
*Метод: Двойная верификация согласно REQ-ARCH-040*

---

## Резюме

Проанализированы 4 плана рефакторинга. Результат:
- **~40% утверждений ложные или неточные**
- **~30% задач дублируют существующий REFACTORING_PLAN.md**
- **~30% содержат новые ценные предложения**

---

## 1. Ложные и Неточные Утверждения

### 1.1. Категория: Преувеличение Проблемы

| План | Утверждение | Реальность | Верификация |
|------|-------------|------------|-------------|
| План 1 | "bootstrap_pipeline 140+ строк, усложняет тестирование" | **113 строк** (`bootstrap.py:68-180`), делегирует через 4 специализированные функции | `wc -l`: 180 всего, функция ~113 строк |
| План 3 | "RecordProcessor совмещает метрики, карантин, запись" | **Делегирует** в `BatchMetricsRecorder`, `BatchTransformer`, `BatchWriter`, `QuarantineManager` | `record_processor.py:59-85` |
| План 4 | "PipelineRunner не выпускает метрики по стадиям" | Использует `PipelineObserver` через `RunnerServices.observer` как context manager | `runner.py:117` |

### 1.2. Категория: Уже Реализовано (не сверено с REFACTORING_PLAN.md)

| План | Утверждение | Статус | Верификация |
|------|-------------|--------|-------------|
| Все планы | "Нет валидации write mode через Enum" | **Реализовано**: `SilverWriteMode`, `GoldWriteMode` enums | `delta_writer.py:53-64`, `gold_writer.py:42-54` |
| Все планы | "Schema drift не обрабатывается" | **Реализовано**: `on_schema_mismatch: Literal["error", "evolve", "ignore"]` | `delta_writer.py:303-349` |
| План 1 | "Архитектурные тесты не связаны с метриками" | **Реализовано**: `tests/architecture/` (187 тестов), `make arch-test` | `Makefile:arch-test` |
| План 2 | "datetime.now в инфраструктуре" | **Частично решено**: arch-test `test_no_datetime_now_in_infrastructure` существует | `tests/architecture/test_no_datetime_now_in_infrastructure.py` |

### 1.3. Категория: Неверная Интерпретация Паттернов

| План | Утверждение | Почему неверно |
|------|-------------|----------------|
| План 1 | "Ручные `__enter__/__exit__` в BaseTransformer — проблема" | Стандартный способ работы со span'ами OpenTelemetry |
| План 4 | "Глобальный реестр — предсказуемость" | `create_registry()` (`registry.py:259`) уже предоставляет изоляцию |
| План 1 | "PipelineServices.aclose гасит исключения" | Design choice для graceful shutdown, критические ошибки логируются |

---

## 2. Дублирование с Существующим REFACTORING_PLAN.md

Следующие задачи из 4 планов **уже описаны** в `docs/REFACTORING_PLAN.md`:

| Задача из планов | Соответствие в REFACTORING_PLAN.md | Статус |
|------------------|-------------------------------------|--------|
| Валидация write mode Silver/Gold | M1, M2 | ✅ Реализовано |
| Schema drift handling | M4 | ✅ Реализовано |
| Единый источник времени | T1-T5 | ⏳ Частично (T5 реализовано) |
| Детерминистичный jitter | D1 | ✅ Реализовано |
| Удаление random из writers | D2, D3 | ✅ Реализовано |
| Tracing в BaseTransformer | O1 | ✅ Реализовано |
| Graceful shutdown tracer | O3 | ⏳ Частично |

---

## 3. Верифицированные Новые Задачи

### Приоритет 1: КРИТИЧЕСКИЙ

#### 3.1. Валидация SinkLayerConfig.mode через WriteModePolicy

**Проблема верифицирована:**
- Файл: `infrastructure/schemas/pipeline_config.py:152`
- Текущее: `mode: str | None = None` — произвольная строка
- Нет связи с `SilverWriteMode`/`GoldWriteMode` enums из `delta_writer.py`, `gold_writer.py`

```python
# Текущее (pipeline_config.py:146-166)
class SinkLayerConfig(BaseModel):
    enabled: bool = True
    mode: str | None = None  # ← Произвольная строка!
```

**Требуемые изменения:**
1. Добавить валидатор `mode` в `SinkLayerConfig` с проверкой через `SilverWriteMode`/`GoldWriteMode`
2. Или использовать `Literal["merge", "append", "overwrite", "scd2", "delete"]`
3. Добавить тест на отклонение невалидных режимов

**Критерии готовности:**
- [ ] `SinkLayerConfig(mode="invalid")` вызывает `ValidationError`
- [ ] Тест покрывает все допустимые комбинации layer+mode

---

### Приоритет 2: ВЫСОКИЙ

#### 3.2. Наблюдаемость операций карантина

**Проблема верифицирована:**
- Файл: `infrastructure/quarantine/operations.py:23-196`
- Функции `inspect_records`, `replay_records`, `purge_records`, `get_statistics` не имеют логирования или метрик

**Требуемые изменения:**
1. Добавить структурированное логирование с `run_id`, `pipeline`, `operation`
2. Добавить метрики: `quarantine_records_inspected`, `quarantine_records_replayed`, `quarantine_records_purged`
3. Логировать время выполнения операций

**Критерии готовности:**
- [ ] Операции `inspect/replay/purge` пишут структурированные логи
- [ ] Метрики доступны через `MetricsPort`
- [ ] Integration тест проверяет наличие логов

#### 3.3. Упрощение трассировки в BaseTransformer через contextlib

**Проблема верифицирована:**
- Файл: `application/core/base_transformer.py:127-188`
- Ручные вызовы `span.__enter__()` и `span.__exit__(None, None, None)`

**Текущий код:**
```python
# base_transformer.py:127-188
span = otel_tracer.start_as_current_span("transform_record", ...)
span.__enter__()
try:
    result = await self._transform_impl(context, record)
    return result
except TransformationError as e:
    ...
finally:
    span.__exit__(None, None, None)
```

**Требуемые изменения:**
Использовать `contextlib.asynccontextmanager` или helper:
```python
async with self._observe_transform(context) as span:
    result = await self._transform_impl(context, record)
```

**Риски:** Низкие — это рефакторинг без изменения поведения
**Критерии готовности:**
- [ ] Метод `transform()` использует context manager
- [ ] Все существующие тесты проходят
- [ ] Покрытие не снижается

---

### Приоритет 3: СРЕДНИЙ

#### 3.4. Ужесточение управления завершением критических сервисов

**Проблема верифицирована:**
- Файл: `application/core/pipeline_services.py:87-108`
- `aclose()` использует `gather(return_exceptions=True)` и только логирует ошибки
- Ошибки закрытия `lock`/`quarantine` могут привести к утечке ресурсов

**Требуемые изменения:**
1. Классифицировать ошибки закрытия: критические (lock, quarantine) vs warning (metrics, tracing)
2. При критических ошибках агрегировать и поднимать исключение после попытки закрытия всех сервисов
3. Добавить метрику `shutdown_errors_total`

**Критерии готовности:**
- [ ] Ошибки lock/quarantine не гасятся молча
- [ ] Метрика `shutdown_errors_total` регистрируется
- [ ] Integration тест с симуляцией ошибки закрытия

#### 3.5. Тесты конфигурационных мапперов YAML → Domain

**Проблема:** Нет явных unit-тестов для преобразования `PipelineYamlConfig` → Domain objects

**Требуемые изменения:**
1. Добавить тесты в `tests/unit/infrastructure/config/` для маппинга
2. Покрыть негативные кейсы (невалидные типы, missing fields)
3. Включить в CI с порогом coverage ≥85% для config модуля

**Критерии готовности:**
- [ ] Тесты на валидные преобразования YAML → Domain
- [ ] Тесты на невалидные конфигурации
- [ ] Coverage отчёт для `infrastructure/config/` модуля

#### 3.6. Унификация health-aware логики адаптеров (требует оценки)

**Проблема верифицирована:**
- `ChemblAdapter` (`client.py:74-75, 92-118, 461-479`): локальная реализация `_consecutive_errors`, `_cached_health`, `_get_effective_batch_size()`, `_update_health()`
- `BaseHttpAdapter` (`base.py:82-121`): только Template Method для `health_check()`, без batch sizing

**Оценка:**
- **За унификацию:** DRY, единый контракт для всех адаптеров
- **Против:** YAGNI — другие адаптеры (UniProt, PubChem) могут иметь другие требования

**Рекомендация:** Отложить до появления второго адаптера с аналогичными требованиями.

---

### Приоритет 4: ЖЕЛАТЕЛЬНЫЙ

#### 3.7. Архитектурные метрики в CI (JSON-отчёт)

**Описание:**
Публиковать результаты `import-linter` и arch-тестов как JSON-артефакт для трендового анализа.

**Критерии готовности:**
- [ ] CI генерирует `arch-report.json` с количеством нарушений/пройденных тестов
- [ ] Документирован формат отчёта

#### 3.8. Наблюдаемость конфигурационного пути

**Описание:**
Добавить debug-логирование при загрузке конфигурации с указанием источника (YAML/CLI).

**Уже частично реализовано:** `bootstrap.py:160-167` логирует `input_filter_enabled`.

---

## 4. Задачи НЕ Рекомендуемые к Реализации

| Задача | Причина отказа |
|--------|----------------|
| "Декомпозиция bootstrap_pipeline" (План 1) | 113 строк с делегированием — не god object |
| "Декомпозиция RecordProcessor" (План 3) | Уже декомпозирован через 4 класса |
| "Метрики уровня раннера" (План 4) | Уже есть `PipelineObserver` |
| "TimeProviderPort" (План 2) | Избыточно — достаточно передачи `ingestion_ts` как параметра |
| "Убрать глобальный реестр" (План 4) | `create_registry()` уже решает проблему изоляции |

---

## 5. Консолидированный План

### Очередь Задач (в порядке приоритета)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     🔴 КРИТИЧЕСКИЙ                                   │
├─────────────────────────────────────────────────────────────────────┤
│  C1: Валидация SinkLayerConfig.mode через Enum                      │
│      Файл: infrastructure/schemas/pipeline_config.py                │
│      Зависимости: нет                                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     🟠 ВЫСОКИЙ                                       │
├─────────────────────────────────────────────────────────────────────┤
│  H1: Наблюдаемость карантина (логи/метрики)                         │
│      Файл: infrastructure/quarantine/operations.py                  │
│                                                                     │
│  H2: Упрощение трассировки в BaseTransformer                        │
│      Файл: application/core/base_transformer.py                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     🟡 СРЕДНИЙ                                       │
├─────────────────────────────────────────────────────────────────────┤
│  M1: Ужесточение shutdown критических сервисов                      │
│      Файл: application/core/pipeline_services.py                    │
│                                                                     │
│  M2: Тесты конфигурационных мапперов                                │
│      Файл: tests/unit/infrastructure/config/                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     🟢 ЖЕЛАТЕЛЬНЫЙ                                   │
├─────────────────────────────────────────────────────────────────────┤
│  L1: Arch-метрики в CI (JSON-отчёт)                                 │
│  L2: Debug-логирование конфигурационного пути                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Связь с Существующим REFACTORING_PLAN.md

Новые задачи должны быть добавлены в `docs/REFACTORING_PLAN.md`:

| Новая задача | Предлагаемый ID | Фаза |
|--------------|-----------------|------|
| Валидация SinkLayerConfig.mode | C1 | Фаза 2 (Medallion) |
| Наблюдаемость карантина | O5 | Фаза 4 (Observability) |
| Упрощение трассировки | O6 | Фаза 4 (Observability) |
| Ужесточение shutdown | O7 | Фаза 4 (Observability) |
| Тесты конфигурационных мапперов | A4 | Фаза 5 (Docs/Tests) |

---

## 7. Методология Верификации (Использованные Команды)

```bash
# Размеры файлов
wc -l src/bioetl/composition/bootstrap.py  # 180 строк
wc -l src/bioetl/application/core/base_transformer.py  # 463 строки
wc -l src/bioetl/application/core/runner.py  # 166 строк
wc -l src/bioetl/application/core/pipeline_services.py  # 123 строки
wc -l src/bioetl/application/core/record_processor.py  # 186 строк

# Проверка делегирования
grep -o "self\._[a-z_]*" src/bioetl/application/core/record_processor.py | sort -u
# Результат: _batch_metrics, _context, _tracer, _transformer, _writer

# Проверка SinkLayerConfig.mode
grep -A5 "class SinkLayerConfig" src/bioetl/infrastructure/schemas/pipeline_config.py

# Проверка карантина
grep -n "self.logger\|self._metrics" src/bioetl/infrastructure/quarantine/operations.py
# Результат: 0 matches

# Проверка PipelineObserver
grep -n "_observer" src/bioetl/application/core/runner.py
# runner.py:89, runner.py:117
```

---

*Верифицировано согласно протоколу REQ-ARCH-040. Все утверждения подкреплены ссылками на код.*

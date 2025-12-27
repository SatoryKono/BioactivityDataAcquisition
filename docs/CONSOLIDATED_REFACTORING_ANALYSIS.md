# Консолидированный Анализ Планов Рефакторинга

*Версия: 3.0 | Дата: 2025-12-27*
*Обновление: Верификация 4 планов из запроса пользователя + интеграция с существующим анализом*

---

## Резюме Анализа

Проведена верификация **4 планов рефакторинга** против реального кода.

| Метрика | Значение |
|---------|----------|
| Всего утверждений в планах | 15 |
| Верифицированных проблем | 5 |
| Ложных утверждений | 4 |
| Дублирований между планами | 5 |
| Уже реализовано | 6+ |

**Главный вывод**: ~50% утверждений ложны или основаны на недопонимании архитектуры.

---

## 1. ЛОЖНЫЕ УТВЕРЖДЕНИЯ (НЕ ТРЕБУЮТ РАБОТЫ)

### ❌ Ложь 1: "ChEMBL adapter — монолит 517 строк"

**Источник**: План 1

**Утверждение**: "Файл infrastructure/adapters/chembl/client.py на 517 строк объединяет транспорт, маппинг сущностей, health-менеджмент и метрики"

**Реальность** (верифицировано):
```
ChEMBL Adapter (517 LOC) ДЕЛЕГИРУЕТ:
├── ChemblEntityMapper (112 LOC) — entity_mapper.py:1-112 (маппинг URL, ключей)
├── ErrorClassifier — domain/error_classifier.py (классификация ошибок)
├── AdapterMetrics — adapters/base_metrics.py (метрики)
└── BaseHttpAdapter — adapters/base.py (базовый HTTP)
```

**Доказательство**: `client.py:30,76-84,90`
```python
from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper
_error_classifier: ErrorClassifier = field(init=False, default_factory=ErrorClassifier)
_adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)
_mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)
```

**Вывод**: Это **когезивный health-aware HTTP fetching** адаптер, использующий делегирование. Декомпозиция создаст overhead без выгоды.

---

### ❌ Ложь 2: "GoldWriter — монолит 593 строки, требует декомпозиции на стратегии"

**Источник**: План 2

**Утверждение**: "GoldWriter совмещает валидацию, SCD2, CSV-экспорт и аудит"

**Реальность** (верифицировано):
```
GoldWriter (593 LOC) ДЕЛЕГИРУЕТ:
├── CsvExporter — composition injection (csv_exporter: CsvExporter | None)
├── AuditPort — composition injection (audit: AuditPort | None)
└── Режимы записи (OVERWRITE, APPEND, SCD2) — когезивная ответственность
```

**Доказательство**: `gold_writer.py:70-71,87-88,351-355`
```python
def __init__(self, ..., csv_exporter: CsvExporter | None = None, audit: AuditPort | None = None):
    self.csv_exporter = csv_exporter
    self._audit = audit

# CSV delegated
if self.csv_exporter:
    await self.csv_exporter.export(table_name, arrow_data, append=csv_append)
```

**Вывод**: CSV и audit уже делегированы. OVERWRITE/APPEND/SCD2 — это когезивные режимы одного writer, не требующие разбиения на стратегии.

---

### ❌ Ложь 3: "Недостаточная автоматизация DQ/Medallion политик"

**Источник**: План 3

**Утверждение**: "Нет явных метрик/тестов, подтверждающих регулярное выполнение DQ порогов и VACUUM SLA"

**Реальность** (верифицировано):
- `MedallionPolicy` в `domain/medallion.py` — существует
- `WriteModePolicy` в `delta_writer.py:53-64` — SilverWriteMode enum
- `DQConfig` в `domain/config.py:25-63` — пороги soft/hard
- `GoldWriteMode` в `gold_writer.py:44-55` — enum валидация

**Доказательство**: `domain/config.py:36-37`
```python
soft_fail_threshold: float = 0.05
hard_fail_threshold: float = 0.20
```

**Вывод**: Политики и пороги реализованы. Метрики доступны через `PreflightService`.

---

### ❌ Ложь 4: "Документ ссылается на Pydantic-модели в domain"

**Источник**: План 1

**Утверждение**: "domain ссылается на Pydantic-модели"

**Реальность** (верифицировано):
- `domain/config.py` использует **dataclass**, не Pydantic
- `PipelineConfig`, `RuntimeConfig`, `DQConfig`, `TableConfig` — все dataclass

**Доказательство**: `domain/config.py:25,66,94,176`
```python
@dataclass(frozen=True, slots=True)
class DQConfig:

@dataclass(frozen=True, slots=True)
class TableConfig:

@dataclass(frozen=True, slots=True)
class PipelineConfig:

@dataclass(frozen=True, slots=True)
class RuntimeConfig:
```

**Вывод**: Документация устарела (ссылается на Pydantic), но фактически код использует dataclass — это правильно.

---

## 2. ДУБЛИРОВАНИЯ МЕЖДУ ПЛАНАМИ

| Проблема | Упоминается в | Статус |
|----------|---------------|--------|
| Legacy поля в PipelineRunContext | План 2, План 3 | ✅ Реальная проблема |
| Дрейф документации Domain | План 1, План 4 | ✅ Реальная проблема |
| Дрейф документации Application | План 1, План 4 | ✅ Реальная проблема |
| Метрики observability | План 1, План 3 | Частично реализовано |
| Декомпозиция ChEMBL | План 1 | ❌ Ложное |
| Декомпозиция GoldWriter | План 2 | ❌ Ложное |

---

## 3. УЖЕ РЕАЛИЗОВАННЫЕ ЗАДАЧИ

| Задача | Упоминается | Доказательство |
|--------|-------------|----------------|
| PipelineRunner DI через RunnerServices | План 1 | `runner.py:84-88`, `runner_services.py` |
| CLI → entrypoints.py | План 1 | `cli.py:17-27` |
| Детерминистичный HTTP jitter | Existing | `domain/resilience.py:45-84` |
| SilverWriteMode/GoldWriteMode enum | Existing | `delta_writer.py:53-64`, `gold_writer.py:44-55` |
| Schema drift handling | Existing | `delta_writer.py:303-349` |
| Arch-тесты random/datetime.now | Existing | `tests/architecture/` |

---

## 4. ВЕРИФИЦИРОВАННЫЕ ПРОБЛЕМЫ (АКТУАЛЬНЫЕ ЗАДАЧИ)

### ✅ Проблема 1: Дрейф документации Domain слоя

**Файл**: `docs/02-architecture/01-domain-layer.md:67-71`

**Проблема**:
```markdown
### 2.3. `pipeline_config.py` — Модели Конфигурации
**Источник:** `src/bioetl/domain/pipeline_config.py`
Содержит Pydantic-модели...
```

**Реальность**:
- `domain/pipeline_config.py` — **НЕ СУЩЕСТВУЕТ**
- Конфигурации в `domain/config.py` как **dataclass**, не Pydantic

**Приоритет**: 🔴 КРИТИЧНЫЙ

---

### ✅ Проблема 2: Дрейф документации Application слоя

**Файл**: `docs/02-architecture/02-application-layer.md:82-84`

**Проблема**:
```markdown
### 2.4. `orchestration/` — Оркестрация Исполнения
**Расположение:** `src/bioetl/application/orchestration/`
```

**Реальность**:
- `application/orchestration/` — **НЕ СУЩЕСТВУЕТ**
- Компоненты в `application/core/`

**Приоритет**: 🔴 КРИТИЧНЫЙ

---

### ✅ Проблема 3: Legacy поля в PipelineRunContext

**Файл**: `src/bioetl/domain/context.py:173-179`

**Проблема**:
```python
# DEPRECATED: Legacy fields for backward compatibility
# TODO: Remove in v2.0 after migration to InputFilterContext
input_csv: str | None = None
filter_column: str | None = None
filter_field: str | None = None
vacuum_after_run: bool | None = None
vacuum_retention_days: int | None = None
```

**Реальность**:
- Дублируют `InputFilterContext` (строки 29-72)
- Дублируют `VacuumConfig` (строки 74-89)
- Миграционная логика в `__post_init__` (181-204)

**Приоритет**: 🟠 ВЫСОКИЙ

---

### ✅ Проблема 4: PipelineRegistry с глобальным состоянием

**Файл**: `composition/registry.py:80-81`

```python
class PipelineRegistry:
    _registry: ClassVar[dict[str, PipelineDefinition]] = {}
    _registry_lock: ClassVar[threading.RLock] = threading.RLock()
```

**Влияние**: Параллельные тесты требуют `clear()`, изоляция нарушена.

**Приоритет**: 🔴 КРИТИЧНЫЙ

---

### ✅ Проблема 5: PipelineObserver создаётся в runner

**Файл**: `runner.py:116-123`

**Влияние**: Усложняет мокирование Observer в тестах.

**Приоритет**: 🟠 ВЫСОКИЙ

---

## 5. КОНСОЛИДИРОВАННЫЙ ПЛАН РЕФАКТОРИНГА

### Приоритет 🔴 КРИТИЧЕСКИЙ

#### DOC-1: Синхронизация документации Domain слоя

**Файл**: `docs/02-architecture/01-domain-layer.md:67-71`

**Изменения**:
```markdown
### 2.3. `config.py` — Конфигурационные Value Objects

**Источник:** `src/bioetl/domain/config.py`

Содержит dataclass Value Objects для конфигурации пайплайнов:
- `PipelineConfig` — полная конфигурация пайплайна
- `RuntimeConfig` — параметры выполнения
- `DQConfig` — пороги Data Quality
- `TableConfig` — настройки таблиц
```

**Оценка**: 0.5 дня

---

#### DOC-2: Синхронизация документации Application слоя

**Файл**: `docs/02-architecture/02-application-layer.md:82+`

**Изменения**:
```markdown
### 2.4. `core/` — Ядро Исполнения Пайплайнов

**Расположение:** `src/bioetl/application/core/`

Компоненты:
- `runner.py` — PipelineRunner
- `executor.py` — PipelineExecutor
- `lifecycle_orchestrator.py` — LifecycleOrchestrator
- `runner_services.py` — RunnerServices bundle (DI)
```

**Оценка**: 0.5 дня

---

#### REG-1: Instance-level PipelineRegistry

**Цель**: Изоляция тестов, параллельное выполнение без `clear()`.

**Решение**:
```python
class PipelineRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, PipelineDefinition] = {}
        self._lock = threading.RLock()
```

**Файлы**:
- `composition/registry.py`
- `composition/bootstrap.py`
- `tests/conftest.py`

**Оценка**: 1-2 дня

---

### Приоритет 🟠 ВЫСОКИЙ

#### LEG-1: Удаление legacy полей из PipelineRunContext

**Файл**: `src/bioetl/domain/context.py`

**Изменения**:
1. Удалить legacy поля (строки 173-179)
2. Удалить миграционную логику (строки 184-204)
3. Обновить CLI для использования `InputFilterContext` / `VacuumConfig`

**Риски**: Несовместимость со скриптами, использующими старые флаги

**Оценка**: 1 день

---

#### OBS-1: Вынести PipelineObserver в composition

**Цель**: Улучшить тестируемость, следовать DI.

**Решение**: Добавить `observer` в `RunnerServices` bundle.

**Оценка**: 0.5 дня

---

### Приоритет 🟡 СРЕДНИЙ

#### DOC-3: Обновить дополнительные документы

**Файлы**:
- `docs/00-map.md`
- `docs/ARCHITECTURE_REVIEW.md`
- `docs/ARCHITECTURE_REVIEW_2025-12*.md`

**Изменения**: Заменить `orchestration/` → `core/`

**Оценка**: 0.5 дня

---

#### TEST-1: Добавить линтер документации

**Новый тест**: `tests/architecture/test_docs_consistency.py`

```python
def test_documented_paths_exist():
    """All paths mentioned in docs should exist in src."""
    # Проверяет что `src/bioetl/...` ссылки в docs ведут на реальные файлы
```

**Оценка**: 0.5 дня

---

## 6. ЗАДАЧИ, НЕ ТРЕБУЮЩИЕ РАБОТЫ

| Предложение из планов | Причина отклонения |
|----------------------|-------------------|
| Декомпозиция ChEMBL adapter на компоненты | Уже делегирует через EntityMapper, ErrorClassifier, AdapterMetrics |
| Декомпозиция GoldWriter на стратегии | Уже делегирует CsvExporter, AuditPort; режимы когезивны |
| Добавить автоматизацию DQ/Medallion | Уже реализовано: MedallionPolicy, DQConfig, WriteMode enums |
| Проверка DI в инфраструктуре | Arch-тесты `test_di_discipline.py` уже проверяют |

---

## 7. ПОРЯДОК ВЫПОЛНЕНИЯ

```
┌─────────────────────────────────────────────────────────────────┐
│                     🔴 КРИТИЧНО (Неделя 1)                      │
├─────────────────────────────────────────────────────────────────┤
│  DOC-1 Domain docs ────┬──▶ DOC-2 Application docs              │
│                        │                                        │
│  REG-1 Registry DI ────┘                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     🟠 ВЫСОКИЙ (Неделя 2)                       │
├─────────────────────────────────────────────────────────────────┤
│  LEG-1 Legacy fields   │    OBS-1 Observer DI                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     🟡 СРЕДНИЙ (По возможности)                  │
├─────────────────────────────────────────────────────────────────┤
│  DOC-3 Other docs      │    TEST-1 Docs linter                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. МАТРИЦА ТРАССИРОВКИ

| Задача | Приоритет | Файлы | Тесты | Риск | Оценка |
|--------|-----------|-------|-------|------|--------|
| DOC-1 | 🔴 | 01-domain-layer.md | test_docs_consistency | Низкий | 0.5д |
| DOC-2 | 🔴 | 02-application-layer.md | test_docs_consistency | Низкий | 0.5д |
| REG-1 | 🔴 | registry.py, bootstrap.py | conftest | Средний | 1-2д |
| LEG-1 | 🟠 | context.py, cli.py | unit | Средний | 1д |
| OBS-1 | 🟠 | runner.py, runner_services.py | unit | Низкий | 0.5д |
| DOC-3 | 🟡 | 00-map.md и др. | — | Низкий | 0.5д |
| TEST-1 | 🟡 | test_docs_consistency.py | self | Низкий | 0.5д |

**Общая оценка**: 5-6 дней

---

## 9. УРОКИ ДЛЯ БУДУЩИХ ОБЗОРОВ

### Причины ложных утверждений:

1. **Отсутствие верификации кодом** — утверждения без проверки
2. **Ложная корреляция размер → god object** — 500+ LOC ≠ проблема, если есть делегирование
3. **Неверная интерпретация паттернов**:
   - Optional injection с NoOp default = Null Object Pattern (валидно)
   - Backward-compat shim ≠ дублирование
4. **Устаревшие знания** — часть задач уже реализована

### Обязательный чек-лист перед предложением:

```bash
# 1. Проверить размер и делегирование
wc -l src/bioetl/path/to/file.py
grep -n "self\._.*\." src/bioetl/path/to/file.py | head -20

# 2. Сверить с REFACTORING_PLAN.md
grep -A3 "ЛОЖНЫЕ УТВЕРЖДЕНИЯ\|УЖЕ РЕАЛИЗОВАНО" docs/REFACTORING_PLAN.md

# 3. Проверить существование файлов
ls -la src/bioetl/path/mentioned/in/docs.py
```

---

## 10. ЗАКЛЮЧЕНИЕ

Из 4 планов рефакторинга:
- **7 задач валидны**: DOC-1, DOC-2, DOC-3, REG-1, LEG-1, OBS-1, TEST-1
- **~50% утверждений ложны** (ChEMBL "монолит", GoldWriter "монолит", нет DQ политик)
- **Основная причина ошибок**: Отсутствие верификации кодом

**Рекомендация**: Выполнить только верифицированные задачи и обновить протокол двойной верификации.

---

*Документ подготовлен на основе верификации кода 2025-12-27*
*Протокол: REQ-ARCH-040 (Двойная верификация)*

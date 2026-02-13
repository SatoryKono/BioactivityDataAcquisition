# RF-CONFIG-STRUCTURE: Консолидированный план рефакторинга

**Версия:** 2.0.0
**Дата:** 2026-02-13
**Статус:** ПРЕДЛОЖЕН
**Источники:**
- Ветка `claude/study-bioetl-config-structure-dljZv` — аудит кода (8 шагов, ~25 файлов)
- Ветка `claude/refactor-config-structure-vyRIX` — план структуры YAML конфигов (6 фаз, ~126 файлов)
- Плюс 4 более ранних codex-ветки, проанализированных в аудите

---

## 1. Краткое резюме

Два независимых анализа дали **взаимодополняющие, но непересекающиеся** планы:

| Аспект | Ветка `dljZv` (Аудит кода) | Ветка `vyRIX` (Структура конфигов) |
|--------|----------------------------|-------------------------------------|
| **Область** | Python код domain/application/infra | YAML конфиг-файлы + загрузчики конфигов |
| **Фокус** | Типобезопасность, DI, convenience-свойства | Унификация именования, дедупликация, структура каталогов |
| **Файлы** | ~25 `.py` файлов | ~126 `.yaml` файлов + ~10 `.py` загрузчиков |
| **Риск** | ВЫСОКИЙ (runtime-поломки при неполной миграции вызовов) | СРЕДНИЙ (обратная совместимость через поддержку алиасов) |
| **Пересечение** | Загрузчики конфигов в infrastructure | Загрузчики конфигов в infrastructure |

Данный документ объединяет оба плана в единый план выполнения с корректным порядком,
управлением зависимостями и набором действенных промптов.

---

## 2. Текущее состояние, верифицированное по кодовой базе

Верифицировано на ветке `master` (коммит `a68e177`):

### 2.1 Подтверждённые проблемы

| ID | Описание | Расположение | Верифицировано |
|----|----------|--------------|----------------|
| **TYPE-1** | `silver_filters: SilverFilterConfig \| GoldFilterConfig \| None` — утечка типа через union | `domain/config/pipeline.py:49` | ДА |
| **TYPE-2** | `SilverFilterConfig(GoldFilterConfig)` — наследование нарушает номинальную типизацию | `domain/filtering/silver_config.py:17` | ДА |
| **TYPE-3** | `TableConfig.silver_write_mode: SilverWriteMode \| str` — остаточный `\| str` | `domain/config/table.py:31` | ДА |
| **DUP-1** | `primary_keys` дублируется в ~50% pipeline-конфигов (top-level, sink.silver.primary_key, sort_by) | `configs/pipelines/` | ДА |
| **DUP-2** | Явные `source_file`, `dq_config_file`, `data_schema_file` в explicit-стиле конфигов | `configs/pipelines/chembl/molecule.yaml` | ДА |
| **DUP-3** | Явные `sink.*.path`, дублирующие конвенционально-вычисляемые пути | То же | ДА |
| **NAME-1** | 4 разных ключа именования DQ-полей (`common_*`, `provider_*`, `entity_*`, `field_*`) | `infrastructure/config/dq_config_loader.py` | ДА |
| **NAME-2** | Сущность `document` в source-конфигах вместо `publication` | `configs/sources/chembl.yaml` | ДА |
| **NAME-3** | `batch_size` дублируется на 2-3 уровнях в source-конфигах | `configs/sources/*.yaml` | ДА |
| **STRUCT-1** | Source-конфиги имеют неоднородную структуру полей между провайдерами | `configs/sources/` | ДА |
| **STRUCT-2** | `data_schema/` содержит 11+ файлов-заглушек (18 строк, `column_groups: []`) | `configs/data_schema/chembl/` | ДА |

### 2.2 Скорректированные утверждения из ветки `dljZv`

| Утверждение | Фактическое состояние |
|-------------|----------------------|
| `write_mode` возвращает `object` | Возвращает `SilverWriteMode \| str` (уже исправлено) |
| `gold_write_mode` возвращает `object` | Возвращает `GoldWriteMode \| str` (уже исправлено) |

Шаг 2 из `dljZv` (исправление return-типов write_mode) **уже выполнен** на master.
Оставшаяся проблема — остаточный `| str` в объявлениях полей `TableConfig`.

---

## 3. Консолидированный план — 6 фаз

### Граф зависимостей

```
Фаза 1: Исправления типов на уровне кода (non-breaking)
    │
    ├──▶ Фаза 2: Улучшение загрузчиков в infrastructure (обратная совместимость)
    │       │
    │       └──▶ Фаза 4: Миграция YAML конфигов
    │               │
    │               └──▶ Фаза 5: Реорганизация каталогов
    │                       │
    │                       └──▶ Фаза 6: Очистка и финализация
    │
    └──▶ Фаза 3: Миграция вызовов и удаление свойств
```

Фазы 1 и 2 можно запускать параллельно.
Фаза 3 зависит от Фазы 1 (исправления типов).
Фаза 4 зависит от Фазы 2 (алиасы в загрузчиках).
Фаза 5 зависит от Фазы 4.
Фаза 6 зависит от всех остальных.

---

### Фаза 1: Исправления типов на уровне кода

**Цель:** Исправить проблемы типобезопасности в domain-слое без изменения поведения.
**Риск:** НИЗКИЙ | **Тесты должны проходить после каждого шага.**

#### Шаг 1.1: Сужение типа `silver_filters`
**Файлы:** 13
**Изменение:** `SilverFilterConfig | GoldFilterConfig | None` → `SilverFilterConfig | None`

Целевые файлы:
- `domain/config/pipeline.py` — объявление поля (строка 49)
- `application/core/base_transformer.py` — сигнатура конструктора
- `application/pipelines/*/transformer.py` — 10 файлов трансформеров
- `composition/factories/pipeline_factory.py`
- `composition/factories/transformer_factory.py`

**Верификация:** `mypy --strict src/bioetl/`

#### Шаг 1.2: Выделение BaseFilterConfig и разрыв наследования SilverFilterConfig
**Файлы:** 4 новых/изменённых
**Изменение:** Разрыв наследования `SilverFilterConfig(GoldFilterConfig)` → оба наследуют `BaseFilterConfig`

```
domain/filtering/
├── _base_filter_config.py   # НОВЫЙ — общая логика (перенесена из gold_config.py)
├── gold_config.py           # ИЗМЕНЁН — GoldFilterConfig(BaseFilterConfig)
├── silver_config.py         # ИЗМЕНЁН — SilverFilterConfig(BaseFilterConfig)
└── __init__.py              # ИЗМЕНЁН — реэкспорт BaseFilterConfig
```

**Ключевое проектное решение:** Общий базовый класс, а НЕ дублирование кода.
- `BaseFilterConfig` содержит `should_include()`, все методы проверок, `_OPERATOR_CHECKERS`
- `GoldFilterConfig` и `SilverFilterConfig` — пустые подклассы для номинальной типизации
- `isinstance(silver, GoldFilterConfig)` становится `False`
- `from_gold_filter_config` → `from_base(other: BaseFilterConfig) -> Self`

Обновления в infrastructure:
- `infrastructure/schemas/filter_config.py` — добавить `to_silver_domain() -> SilverFilterConfig`
- `infrastructure/config/filter_config_loader.py` — обновить возвращаемый тип
- `infrastructure/config/_base.py` — обновить вызов фабрики

**Верификация:** `mypy --strict` + юнит-тесты фильтров

#### Шаг 1.3: Сужение типов write mode в TableConfig (опционально)
**Файлы:** 2-3
**Изменение:** `SilverWriteMode | str` → `SilverWriteMode` в `TableConfig`

Только если подтверждено, что вся конвертация string→enum происходит на границе infrastructure.
Перенести конвертацию в `infrastructure/config/_base.py` в `yaml_config_to_domain()`.

**Верификация:** Все интеграционные тесты загрузки конфигов

---

### Фаза 2: Улучшение загрузчиков в infrastructure

**Цель:** Добавить обратно-совместимую поддержку алиасов в загрузчики конфигов,
чтобы новые имена полей YAML работали наравне со старыми.
**Риск:** СРЕДНИЙ | **Ноль breaking changes — старые конфиги продолжают работать.**

#### Шаг 2.1: Загрузчик DQ конфигов — унифицированные имена полей
**Файл:** `infrastructure/config/dq_config_loader.py`
**Изменение:** Принимать как старые ключи (`common_field_validations`, `provider_field_validations`,
`entity_field_validations`), так и новый универсальный ключ (`field_validations`) на всех уровнях иерархии.

```python
# Нормализация в загрузчике:
# Если файл на уровне defaults и содержит "field_validations" → трактовать как "common_field_validations"
# Если файл на уровне provider и содержит "field_validations" → трактовать как "provider_field_validations"
# Если файл на уровне entity и содержит "field_validations" → трактовать как "entity_field_validations"
# Старые ключи по-прежнему работают для обратной совместимости.
```

Аналогично для `cross_field_validations` и `conditional_validations`.

#### Шаг 2.2: Загрузчик DQ конфигов — алиас `dq_overrides`
**Файл:** `infrastructure/config/pipeline_config_loader.py`
**Изменение:** Принимать `dq_overrides` как алиас для `dq_rules` в pipeline-конфигах.

#### Шаг 2.3: Source-конфиги — поддержка нормализованной структуры
**Файл:** `composition/providers/_config_helpers.py`
**Изменение:** Поддержка как старой вложенной структуры, так и новой плоской.

Старая: `source.provider_config.base_url`
Новая: `api.base_url`

Использовать Pydantic `model_validator` или ручную нормализацию для приёма обоих форматов.

#### Шаг 2.4: Загрузчик конфигов фильтров — алиас пути
**Файл:** `infrastructure/config/filter_config_loader.py`
**Изменение:** Принимать путь `configs/filters/` наряду с `configs/filter/`.

#### Шаг 2.5: Загрузчик схем данных — алиас пути
Принимать `configs/schemas/` наряду с `configs/data_schema/`.

**Верификация:** Существующие тесты проходят без изменений (старый формат всё ещё работает).

---

### Фаза 3: Миграция вызовов и удаление свойств

**Цель:** Мигрировать все вызовы с convenience-свойств на `config.table.*`
и удалить свойства.
**Риск:** ВЫСОКИЙ | **Необходимо верифицировать ВСЕ вызовы перед удалением.**

#### Шаг 3.1: Добавить `effective_silver_table` / `effective_gold_table`
**Файл:** `domain/config/pipeline.py`
**Изменение:** Добавить два централизованных свойства с fallback-логикой:

```python
@property
def effective_silver_table(self) -> str:
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"
```

#### Шаг 3.2: Миграция ВСЕХ вызовов
**Полная инвентаризация (верифицирована через grep):**

| Файл | Старое использование | Новое использование |
|------|---------------------|---------------------|
| `application/services/medallion_lifecycle.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `application/core/preflight_service.py` | `config.write_mode`, `config.gold_write_mode` | `config.table.silver_write_mode`, `config.table.gold_write_mode` |
| `composition/factories/services_factory.py` | Все 7 свойств | `config.table.*` / `config.effective_*` |
| `composition/_resource_management.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `composition/bootstrap/cli/storage.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `application/composite/dependency_coordinator.py` | `source_config.silver_table` (8 раз) | `source_config.effective_silver_table` |

**Верификация:** `grep -rn 'config\.\(silver_table\|gold_table\|write_mode\|gold_write_mode\|primary_keys\|partition_cols\|on_schema_mismatch\)' src/bioetl/ --include="*.py"` возвращает 0 результатов (кроме самих свойств и тестов).

#### Шаг 3.3: Удаление convenience-свойств
**Файл:** `domain/config/pipeline.py`
**Удалить:** свойства `primary_keys`, `silver_table`, `gold_table`, `write_mode`,
`gold_write_mode`, `partition_cols`, `on_schema_mismatch`.

**Оставить:** `effective_silver_table`, `effective_gold_table`, `lock_key`.

#### Шаг 3.4: Обновление тестов
Обновить все тестовые файлы, ссылающиеся на удалённые свойства.

---

### Фаза 4: Миграция YAML конфигов

**Цель:** Упростить YAML-конфиги: убрать дублирование, унифицировать именование, convention-based минимальный стиль.
**Риск:** СРЕДНИЙ | **Загрузчики из Фазы 2 обеспечивают обратную совместимость при миграции.**

#### Шаг 4.1: Исправление имён сущностей в source-конфигах
**Файлы:** `configs/sources/chembl.yaml` (и другие, содержащие `document`)
**Изменение:** `document` → `publication`, `document_similarity` → `publication_similarity` и т.д.

#### Шаг 4.2: Упрощение pipeline-конфигов — удаление дублированных полей
**Файлы:** ~30 YAML-файлов pipeline-конфигов
**Удалить из каждого:**
- `source_file` (вычисляется по конвенции)
- `dq_config_file` (вычисляется по конвенции)
- `data_schema_file` (вычисляется по конвенции)
- `sink.*.path` (вычисляется по конвенции)
- `sink.silver.primary_key` (авто-пробрасывается из `primary_keys`)
- `sink.*.sort_by.columns` (авто-пробрасывается)
- `sink.*.csv_export.path` (авто-вычисляется из пути sink)

**Переименовать:** `dq_rules` → `dq_overrides`

#### Шаг 4.3: Унификация именования DQ полей
**Файлы:** ~39 DQ YAML-файлов
**Изменение во всех файлах:** Использовать `field_validations` повсеместно вместо
`common_field_validations` / `provider_field_validations` / `entity_field_validations`.
Аналогично для `cross_field_validations` и `conditional_validations`.

#### Шаг 4.4: Нормализация source-конфигов
**Файлы:** 7 YAML-файлов source-конфигов
**Изменение:** Реструктуризация к единой схеме:

```yaml
version: "1.0.0"
api:
  base_url: ...
  auth_type: public | email | api_key
client:
  timeout_sec: 60.0
  max_retries: 3
batch:
  api_batch_size: 10
  page_size: 100
rate_limit:
  default:
    requests_per_second: 3
    burst: 10
  authenticated: ...  # опционально
health_check:
  endpoint: ...
  timeout_sec: 5
entities:
  - activity
  - publication  # канонические имена
```

#### Шаг 4.5: Уменьшение _base.yaml
**Файл:** `configs/pipelines/_base.yaml` (491 → ~150 строк)
**Изменение:** Перенести документацию в `docs/03-guides/CONFIG-GUIDE.md`, оставить только значения по умолчанию + краткие комментарии.

#### Шаг 4.6: Очистка заглушек `data_schema/`
**Удалить:** Все 18-строчные файлы-заглушки с `column_groups: []`
Загрузчики конфигов должны корректно обрабатывать отсутствие файла (пустой конфиг).

**Верификация:** Полный набор тестов пайплайнов, `bioetl config validate` (если существует).

---

### Фаза 5: Реорганизация каталогов

**Цель:** Единообразное именование и логическая группировка.
**Риск:** СРЕДНИЙ | **Загрузчики с алиасами путей из Фазы 2 гарантируют отсутствие поломок.**

| Старый путь | Новый путь | Обоснование |
|-------------|-----------|-------------|
| `configs/dq/` | `configs/quality/` | Более понятное имя |
| `configs/filter/` | `configs/filters/` | Единообразие множественного числа |
| `configs/data_schema/` | `configs/schemas/` | Короче, стандартнее |
| `configs/composite/field_groups/` | `configs/schemas/composite/field_groups/` | Размещение рядом со схемами |
| `configs/pipelines/_schema.json` | `configs/_schema/pipeline.json` | Отделение от YAML |
| `configs/pipelines/_composite_schema.json` | `configs/_schema/composite.json` | То же |

**Порядок выполнения:**
1. Создать новые каталоги
2. Скопировать файлы (не перемещать — старые пути работают через алиасы)
3. Запустить полный набор тестов
4. Удалить старые каталоги

**Верификация:** Все интеграционные тесты + `find configs/ -name '*.yaml' | wc -l` без изменений.

---

### Фаза 6: Очистка и финализация

#### Шаг 6.1: Удаление алиасов обратной совместимости из загрузчиков
Удалить алиасы старых ключей, fallback на старые пути.

#### Шаг 6.2: Обновление документации
- ADR-027 (экстернализация DQ) — новые пути
- ADR-028 (экстернализация фильтров) — новые пути
- ADR-029 (конвенционные пути) — новые имена каталогов
- RULES.md — ссылки на конфиги

#### Шаг 6.3: Очистка `validation.py`
**Файл:** `domain/config/validation.py`
**Удалить:** Комментарии-разделители секций (`# ============`), избыточную многословность в docstring модуля.
**Сохранить:** Docstring-и атрибутов (диапазоны годов публикаций, молекулярных масс), пояснения типов валидации, комментарии к вариантам условий.

#### Шаг 6.4: Архитектурные тесты
Новые тесты:
- `SilverFilterConfig` НЕ является подклассом `GoldFilterConfig`
- `isinstance(SilverFilterConfig(...), GoldFilterConfig)` — `False`
- Граница импортов: ни один код за пределами `domain/filtering/` не импортирует `_base_filter_config` напрямую
- Загрузка конфигов: старый формат → новый формат даёт идентичные доменные объекты
- Логика fallback `effective_silver_table` / `effective_gold_table`

#### Шаг 6.5: Опционально — `bioetl config show <pipeline>`
CLI-команда, показывающая resolved-конфиг после всех слияний — полезна для отладки.

---

## 4. Матрица рисков

| Фаза | Риск | Последствия при ошибке | Митигация |
|------|------|------------------------|-----------|
| 1 (Исправления типов) | НИЗКИЙ | Только ошибки mypy | `mypy --strict` после каждого шага |
| 2 (Алиасы в загрузчиках) | СРЕДНИЙ | Регрессия загрузки конфигов | Интеграционные тесты, поддержка двух форматов |
| 3 (Миграция вызовов) | **ВЫСОКИЙ** | Runtime `AttributeError` | Исчерпывающий grep, поэтапное удаление |
| 4 (Миграция YAML) | СРЕДНИЙ | Некорректные resolved-конфиги | Миграционные тесты, алиасы из Фазы 2 как страховка |
| 5 (Реорганизация каталогов) | СРЕДНИЙ | Ошибки file-not-found | Алиасы путей как страховка |
| 6 (Очистка) | НИЗКИЙ | Расхождение документации | Чек-лист ревью |

---

## 5. Метрики

| Метрика | До | После | Цель |
|---------|-----|-------|------|
| Суммарный LOC YAML в `configs/` | ~4 500 | ~3 000 | -30% |
| Максимальный LOC pipeline-конфига | 117 (molecule) | ~40 | -60% |
| Дублированных primary_keys | ~50 пар | 0 | 0 |
| Вариантов ключей DQ-валидации | 4 | 1 | 1 |
| Стилей pipeline-конфигов | 3 | 1 (convention-based) | 1 |
| `isinstance(silver, GoldFilter)` | `True` (неверно) | `False` (верно) | Исправлено |
| Convenience-свойств на PipelineConfig | 7 | 2 (`effective_*`) | Минимум |

---

## 6. Сводка по изменённым файлам

| Фаза | Новые файлы | Изменённые файлы | Удалённые файлы |
|------|-------------|------------------|-----------------|
| 1 | 1 (`_base_filter_config.py`) | ~18 | 0 |
| 2 | 0 | ~6 загрузчиков | 0 |
| 3 | 0 | ~8 вызывающих модулей + pipeline.py | 0 |
| 4 | 1 (`CONFIG-GUIDE.md`) | ~100 YAML + 0 .py | ~11 заглушек |
| 5 | 0 | ~6 загрузчиков (обновление путей) | старые каталоги |
| 6 | 3-5 тестовых файлов | ~5 документов | код алиасов |
| **Итого** | **~6** | **~130** | **~15** |

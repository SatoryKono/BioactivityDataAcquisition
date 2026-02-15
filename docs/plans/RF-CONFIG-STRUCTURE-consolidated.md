# RF-CONFIG-STRUCTURE: Консолидированный план рефакторинга

**Версия:** 3.0.0
**Дата:** 2026-02-15
**Статус:** В РАБОТЕ
**Источники:**
- Ветка `claude/study-bioetl-config-structure-dljZv` — аудит кода
- Ветка `claude/refactor-config-structure-vyRIX` — план структуры YAML конфигов
- Синхронизировано с `main` (коммит `2c360d5`, 2026-02-15)

---

## 1. Прогресс выполнения

| Фаза | Шаг | Статус | Выполнено в |
|------|-----|--------|-------------|
| **1** | 1.1: Сужение типа `silver_filters` | ✅ ВЫПОЛНЕНО | PR #2122 |
| **1** | 1.2: Выделение BaseFilterConfig | ❌ НЕ НАЧАТО | — |
| **1** | 1.3: Сужение write_mode типов | ⚠️ ЧАСТИЧНО | PR #2122 (конвертация на границе есть, `\| str` в объявлении остался) |
| **2** | 2.1: DQ загрузчик — fallback путей | ✅ ВЫПОЛНЕНО | PR #2122 (`configs/quality/` + `configs/dq/`) |
| **2** | 2.2: Алиас `dq_overrides` | ✅ ВЫПОЛНЕНО | PR #2122/2123 (Pydantic AliasChoices) |
| **2** | 2.3: Source-конфиги — двойной формат | ❌ НЕ НАЧАТО | — |
| **2** | 2.4: Filter загрузчик — fallback путей | ✅ ВЫПОЛНЕНО | PR #2122 (`configs/filters/` + `configs/filter/`) |
| **2** | 2.5: Schemas загрузчик — fallback путей | ✅ ВЫПОЛНЕНО | PR #2122 |
| **2** | 2.6: Convention-based defaults | ✅ ВЫПОЛНЕНО | PR #2123 (`config_loader.py` +216 строк) |
| **3** | 3.1-3.4: Миграция вызовов и удаление свойств | ❌ НЕ НАЧАТО | — |
| **4** | 4.1-4.6: Миграция YAML конфигов | ⚠️ МИНИМАЛЬНО | Только косметические правки в DQ/molecule.yaml |
| **5** | Реорганизация каталогов | ❌ НЕ НАЧАТО | Загрузчики готовы (fallback есть) |
| **6** | Очистка и финализация | ⚠️ ЧАСТИЧНО | Архитектурные тесты добавлены (medallion, path contracts) |

---

## 2. Оставшиеся задачи

### Граф зависимостей (только оставшееся)

```
Шаг 1.2: BaseFilterConfig extraction
    │
    └──▶ Шаг 1.3: Финализация write_mode (опционально)

Шаг 2.3: Source-конфиг двойной формат (опционально)
    │
    └──▶ Фаза 4: Миграция YAML
            │
            └──▶ Фаза 5: Реорганизация каталогов
                    │
                    └──▶ Фаза 6: Очистка

Фаза 3: Миграция вызовов (независима от Фазы 4)
```

---

### Шаг 1.2: Выделение BaseFilterConfig (НЕ НАЧАТО)

**Проблема:** `SilverFilterConfig(GoldFilterConfig)` в `domain/filtering/silver_config.py:17`.
`isinstance(silver_cfg, GoldFilterConfig)` возвращает `True` — нарушение номинальной типизации.

**Целевая структура:**
```
domain/filtering/
├── _base_filter_config.py   # НОВЫЙ — вся логика (should_include, _check_*, _OPERATOR_CHECKERS)
├── gold_config.py           # GoldFilterConfig(BaseFilterConfig) — пустое тело
├── silver_config.py         # SilverFilterConfig(BaseFilterConfig) — пустое тело
└── __init__.py              # реэкспорт
```

**Обновления в infrastructure (уже частично подготовлены):**
- `infrastructure/schemas/filter_config.py` — `SilverFiltersFileConfig.to_domain()` уже возвращает `SilverFilterConfig`
- `infrastructure/config/_base.py` — `_build_silver_filters()` уже вызывает `SilverFilterConfig.from_gold_filter_config()`
- `infrastructure/config/filter_config_loader.py` — уже возвращает `SilverFilterConfig`

**Файлы:** ~7 (1 новый + 6 изменённых)
**Риск:** СРЕДНИЙ

---

### Шаг 1.3: Финализация write_mode типов (ЧАСТИЧНО)

**Текущее состояние:** `TableConfig` объявляет `silver_write_mode: SilverWriteMode | str`,
но `__post_init__` конвертирует строки в enum. `_base.py` уже конвертирует на границе
через `SilverWriteMode.from_string()`.

**Оставшееся:** Убрать `| str` из объявлений в `domain/config/table.py:31-32`.
**Файлы:** 1-2
**Риск:** НИЗКИЙ

---

### Шаг 2.3: Source-конфиги — двойной формат (НЕ НАЧАТО, опционально)

**Файл:** `composition/providers/_config_helpers.py`
**Изменение:** Нормализация нового плоского формата (`api.base_url`) в старый (`source.provider_config.base_url`).

Этот шаг **опционален** — можно мигрировать YAML напрямую (Шаг 4.4) без промежуточной
поддержки двух форматов, если делать атомарно (конфиги + загрузчик одним коммитом).

---

### Фаза 3: Миграция вызовов и удаление свойств (НЕ НАЧАТО)

**Текущее состояние `domain/config/pipeline.py`** (после merge с main):
- Строка 49: `silver_filters: SilverFilterConfig | None = None` ✅ (уже исправлено)
- Строки 112-145: 7 convenience-свойств ВСЁ ЕЩЁ ПРИСУТСТВУЮТ

**Шаги:**
1. Добавить `effective_silver_table` / `effective_gold_table`
2. Мигрировать все вызовы `config.primary_keys` → `config.table.primary_keys` и т.д.
3. Удалить 7 convenience-свойств
4. Обновить тесты

**Файлы:** ~8 вызывающих модулей + pipeline.py + тесты
**Риск:** ВЫСОКИЙ

---

### Фаза 4: Миграция YAML конфигов (НЕ НАЧАТО)

Загрузчики из Фазы 2 уже поддерживают оба формата. Можно безопасно мигрировать:

| Шаг | Описание | Файлы |
|-----|----------|-------|
| 4.1 | `document` → `publication` в source-конфигах | `configs/sources/chembl.yaml` |
| 4.2 | Удаление дублей из pipeline-конфигов (paths, primary_key, sort_by) | ~30 YAML |
| 4.3 | Унификация DQ ключей (`common_*` / `provider_*` / `entity_*` → `field_validations`) | ~39 YAML |
| 4.4 | Нормализация source-конфигов к плоской схеме | 7 YAML |
| 4.5 | Slim down `_base.yaml` (491 → ~150 строк) | 1 YAML + 1 MD |
| 4.6 | Удаление файлов-заглушек `data_schema/` | ~11 YAML |

**Риск:** СРЕДНИЙ (fallback-алиасы страхуют)

---

### Фаза 5: Реорганизация каталогов (НЕ НАЧАТО, готово к выполнению)

Загрузчики УЖЕ поддерживают новые пути (`configs/quality/`, `configs/filters/`, `configs/schemas/`).
Осталось:
1. Скопировать файлы в новые каталоги
2. Прогнать тесты
3. Удалить старые каталоги

---

### Фаза 6: Очистка и финализация (ЧАСТИЧНО)

**Уже выполнено:**
- ✅ `tests/architecture/test_medallion_policy.py` — тест ARCH-007
- ✅ `tests/architecture/test_path_contracts.py` — тест ADR-025

**Осталось:**
- Удаление fallback-кода из загрузчиков
- Обновление ADR-027, ADR-028, ADR-029
- Тесты на разделение BaseFilterConfig/Gold/Silver
- Тесты на `effective_*_table`
- Опционально: `bioetl config show <pipeline>`

---

## 3. Обновлённая матрица рисков

| Задача | Риск | Последствия | Митигация |
|--------|------|-------------|-----------|
| BaseFilterConfig extraction (1.2) | СРЕДНИЙ | mypy ошибки, сломанные тесты фильтрации | Юнит-тесты фильтров, `mypy --strict` |
| Миграция вызовов (Фаза 3) | **ВЫСОКИЙ** | Runtime `AttributeError` | Исчерпывающий grep, поэтапное удаление |
| Миграция YAML (Фаза 4) | НИЗКИЙ | Уже есть fallback | Тесты загрузки конфигов |
| Реорганизация каталогов (Фаза 5) | НИЗКИЙ | Уже есть fallback путей | Copy→test→delete |
| Очистка (Фаза 6) | НИЗКИЙ | Документация | Чек-лист ревью |

---

## 4. Целевые метрики (обновлены)

| Метрика | До (v1) | Сейчас (main) | Цель |
|---------|---------|---------------|------|
| `silver_filters` тип | Union leak | ✅ `SilverFilterConfig \| None` | Исправлено |
| `isinstance(silver, Gold)` | `True` | `True` (ещё не исправлено) | `False` |
| Path fallback в загрузчиках | Нет | ✅ Есть | Есть |
| `dq_overrides` алиас | Нет | ✅ Есть (AliasChoices) | Есть |
| Convention defaults | Нет | ✅ `config_loader.py` +216 строк | Есть |
| LOC в `configs/` | ~4 500 | ~4 500 | ~3 000 (-30%) |
| Стилей pipeline-конфигов | 3 | 3 | 1 |
| Convenience-свойств | 7 | 7 | 2 (`effective_*`) |

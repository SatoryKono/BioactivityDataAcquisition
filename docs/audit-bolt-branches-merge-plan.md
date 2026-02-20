# Аудит Bolt-веток и План Объединения с Main

**Дата аудита:** 2026-02-20
**Базовый коммит main:** `9c0ff3bda` (feat(api): add new ports for metrics extraction and runnable tasks)
**Количество проанализированных веток:** 27

---

## Оглавление

1. [Общая сводка](#1-общая-сводка)
2. [Классификация по совместимости с main](#2-классификация-по-совместимости-с-main)
3. [Группировка по области изменений](#3-группировка-по-области-изменений)
4. [Рекомендации: что объединять](#4-рекомендации-что-объединять)
5. [План объединения](#5-план-объединения)
6. [Ветки к удалению](#6-ветки-к-удалению)

---

## 1. Общая сводка

| Категория | Кол-во | Описание |
|-----------|--------|----------|
| **Чистый merge возможен** | 3 | Есть общий предок с main, merge без конфликтов |
| **Merge с конфликтами** | 2 | Есть общий предок, но есть конфликты |
| **Orphaned (нет общего предка)** | 22 | История разошлась с main, прямой merge невозможен |

**Ключевое наблюдение:** 22 из 27 веток (81%) не имеют общего предка с текущим main. Это означает, что main был перезаписан (force-push / rebase) после создания этих веток. Все orphaned-ветки содержат сотни изменений в файлах, не связанных с целевой оптимизацией (конфигурации `.aiassistant/`, `.claude/`, схемы, domain и т.д.), что делает прямой merge невозможным.

---

## 2. Классификация по совместимости с main

### Ветки с общим предком (MERGEABLE)

| Ветка | Дата | Merge статус | Файлы (целевые) |
|-------|------|-------------|-----------------|
| `bolt/optimize-date-extractor-2826375097710156585` | 2026-02-15 | **CLEAN** | `extractors/date.py`, +тесты |
| `bolt-optimize-pubmed-identifiers-9455405533693776821` | 2026-02-17 | **CLEAN** | `extractors/identifier.py`, `transformer.py`, +`identifier_types.py` |
| `bolt-pubmed-identifier-opt-169219971728294416` | 2026-02-14 | **CLEAN** (individual) | `extractors/identifier.py`, `transformer.py` |
| `bolt/uniprot-feature-optimization-1706687305301958106` | 2026-02-12 | **CONFLICTS** (features.py) | `extractors/features.py` |
| `bolt-optimize-pubmed-identifiers-17563303524360502919` | 2026-02-16 | **CONFLICTS** (3 files) | `extractors/identifier.py`, +`identifier_helper.py`, +`identifier_types.py`, `transformer.py`, `_author_helpers.py`, `author_normalization_service.py` |

### Orphaned ветки (НЕТ ОБЩЕГО ПРЕДКА)

Все остальные 22 ветки — orphaned. Они содержат от 100 до 420+ изменённых файлов, что делает cherry-pick единственным способом извлечения полезных изменений.

---

## 3. Группировка по области изменений

### Группа A: Silver Writer (12 веток)

**Целевой файл:** `src/bioetl/infrastructure/storage/silver_writer.py`

| Ветка | Дата | Статус | Diff lines | Оптимизация |
|-------|------|--------|-----------|-------------|
| `bolt-silver-writer-perf-5880266767462610852` | 01-21 | Orphaned | 479 | Самая крупная переработка цикла сериализации |
| `bolt/optimize-batch-writer-gold-8224212234072549004` | 01-20 | Orphaned | — | Не silver, но gold (см. Gold) |
| `bolt-optimize-silver-writer-6952166425433176391` | 01-24 | Orphaned | 275 | Сериализация + fix PreflightReport TypeError |
| `bolt-optimize-silver-writer-2356727444240081857` | 01-25 | Orphaned | 261 | Record preparation |
| `bolt/optimize-silver-writer-13553046753343703003` | 01-25 | Orphaned | 296 | Record preparation + dedup |
| `bolt/optimize-silver-writer-14305130312494082531` | 01-26 | Orphaned | 265 | Record preparation |
| `bolt-silver-writer-optimization-7894939204007800549` | 01-27 | Orphaned | 263 | Preparation loop |
| `bolt/optimize-silver-writer-5061550331081307667` | 01-28 | Orphaned | 233 | Arrow data schema filtering |
| `bolt/silver-writer-optimization-8085015874627325572` | 01-29 | Orphaned | 137 | + Semantic Scholar pipeline refactor |
| `bolt-silver-writer-optimization-11154284540065872566` | 02-01 | Orphaned | 221 | Filtering + compliance (4.8x speedup заявлено) |
| `bolt/optimize-silver-writer-4539369462564194106` | 02-02 | Orphaned | 171 | Loop optimization (2x speedup) |
| `bolt/optimize-silver-writer-filtering-16275368554400671306` | 02-05 | Orphaned | 158 | Schema filtering + Mypy fixes |
| `bolt-silver-writer-optimization-4078771543740170219` | 02-11 | Orphaned | 174 | Наиболее свежая итерация |

**Общий паттерн оптимизации во всех ветках:**
```python
# БЫЛО (main): итерация по всем полям записи, фильтрация по схеме
filtered = [{k: v for k, v in rec.items() if k in schema_fields} for rec in records]

# СТАЛО: итерация по полям СХЕМЫ (меньше), lookup в записи
for rec in records:
    new_rec = {}
    for name in schema.names:      # O(schema) вместо O(record)
        if name in rec:
            new_rec[name] = rec[name]
```

**Дополнительные изменения (в некоторых ветках):**
- Удаление `_validate_key_nullability()` (спорно — убирает валидацию)
- Удаление фильтрации `_state` перед валидацией (рискованно)
- Рефакторинг импортов (`ArrowTypeError` → `pa.ArrowTypeError`)

**Рекомендация:** Cherry-pick паттерна оптимизации цикла из `bolt-silver-writer-optimization-4078771543740170219` (самая свежая, чистый код). **НЕ** включать удаление `_validate_key_nullability()` без обоснования.

---

### Группа B: Gold Writer / Batch Writer (2 ветки)

**Целевые файлы:** `gold_writer.py`, `batch_writer.py`

| Ветка | Дата | Статус | Оптимизация |
|-------|------|--------|-------------|
| `bolt/gold-writer-optimization-9251521540080561602` | 01-22 | Orphaned | Удаление column ordering, GoldMetadataBuilder |
| `bolt/optimize-batch-writer-gold-8224212234072549004` | 01-20 | Orphaned | In-place filtering, кэш `_gold_schema_columns` |

**Ветка 1 (gold-writer-optimization):**
- Чистое удаление ColumnOrderer/schema normalization
- Извлечение GoldMetadataBuilder
- Объединение validate+convert в один executor
- **Качество: ХОРОШЕЕ** — упрощение без потери абстракций

**Ветка 2 (optimize-batch-writer-gold):**
- In-place мутация записей (вместо создания новых dict)
- Инлайн metadata building (180+ LOC) — **потеря maintainability**
- Удаление ArrowDataConverter abstraction
- **Качество: СМЕШАННОЕ** — быстрее, но менее поддерживаемый код

**Рекомендация:** Cherry-pick идей из ветки 1 (чище). Ветку 2 — отклонить (инлайн 180 LOC metadata — антипаттерн).

---

### Группа C: PubMed Date Parsing (6 веток)

| Ветка | Дата | Статус | Diff в date.py | Оптимизация |
|-------|------|--------|---------------|-------------|
| `bolt/optimize-date-extractor-2826375097710156585` | 02-15 | **MERGEABLE** | 74 lines | Singleton + class var + calendar import |
| `bolt-pubmed-date-extraction-optimization-10719411922497146945` | 01-30 | Orphaned | 34 lines | Lightweight singleton |
| `bolt-perf-pubmed-transformer-date-5922893198129129252` | 02-07 | Orphaned | 13 lines | PubMedDateHelper delegation |
| `bolt-optimize-pubmed-date-3789117081982362004` | 02-11 | Orphaned | 0 (!) | Изменения в transformer.py, не в date.py |
| `bolt-optimize-pubmed-date-parsing-8283081052165591821` | 02-08 | Orphaned | 0 (!) | Аналогично — date.py не тронут |
| `bolt-perf-pubmed-date-parsing-12532949572236019825` | 02-12 | Orphaned | 0 (!) | Аналогично — date.py не тронут |

**Критическое наблюдение:** 3 ветки с "date" в названии на самом деле НЕ изменяют `date.py`! Их изменения — в `transformer.py` и других файлах, но из-за orphaned-статуса diff показывает сотни несвязанных файлов.

**Рекомендация:** Merge `bolt/optimize-date-extractor-2826375097710156585` — единственная чистая, конкретная оптимизация. Остальные — отклонить.

---

### Группа D: PubMed Identifiers (3 ветки)

| Ветка | Дата | Статус | Подход |
|-------|------|--------|--------|
| `bolt-optimize-pubmed-identifiers-9455405533693776821` | 02-17 | **MERGEABLE** | Integrated: single-pass XML, `identifier_types.py`, walrus operators |
| `bolt-pubmed-identifier-opt-169219971728294416` | 02-14 | **MERGEABLE** (individual) | Aggressive: deprecate old methods, plain dict returns |
| `bolt-optimize-pubmed-identifiers-17563303524360502919` | 02-16 | **CONFLICTS** | Module extraction: `identifier_helper.py` + `identifier_types.py` + domain changes |

**ВАЖНО:** Ветки 1 и 3 конфликтуют друг с другом (оба меняют `identifier.py` и `transformer.py`). Нужно выбрать ОДНУ.

**Сравнение подходов:**

| Критерий | Ветка 9455... | Ветка 169219... | Ветка 17563... |
|----------|-------------|---------------|---------------|
| Новые файлы | 1 (`identifier_types.py`) | 0 | 2 (`identifier_helper.py`, `identifier_types.py`) |
| Чистота merge | Clean | Clean | Конфликты |
| Type safety | TypedDict | plain dict (потеря!) | TypedDict |
| Backward compat | Хорошая | Deprecation warnings | Хорошая |
| Сложность | Средняя | Низкая | Высокая |
| Domain changes | Нет | Нет | Да (ports, services) |

**Рекомендация:** Merge `bolt-optimize-pubmed-identifiers-9455405533693776821` — оптимальный баланс чистоты, type safety и простоты.

---

### Группа E: PubMed Transformer (2 ветки)

| Ветка | Дата | Статус |
|-------|------|--------|
| `bolt/pubmed-transformer-optimization-1564101723275582547` | 02-13 | Orphaned |
| `bolt-pubmed-optimization-11776621839494351834` | 02-11 | Orphaned |

Обе orphaned, затрагивают десятки файлов. Целевые изменения в `transformer.py` (удаление service calls, инлайн month_map, static methods). Идеи полезные, но merge невозможен.

**Рекомендация:** Cherry-pick специфических идей вручную после стабилизации main.

---

### Группа F: UniProt Feature Optimization (1 ветка)

| Ветка | Дата | Статус |
|-------|------|--------|
| `bolt/uniprot-feature-optimization-1706687305301958106` | 02-12 | **CONFLICTS** |

Единственная ветка. Оптимизация: pre-normalization паттернов, walrus operators, ~7% speedup.
Конфликт в `features.py` — нужен ручной resolve.

**Рекомендация:** Merge с ручным разрешением конфликта — оптимизация простая и полезная.

---

### Группа G: Silver Serialization (1 ветка)

| Ветка | Дата | Статус |
|-------|------|--------|
| `bolt/optimize-silver-serialization-17048994287352894847` | 02-11 | Orphaned |

**420 файлов изменено, 13900+ / 18507- строк.** Это фактически полная переработка кодовой базы, а не оптимизация silver serialization. Включает:
- Переименование модулей (`xml_parser.py` → `xml_utils.py`)
- Удаление целых модулей (domain/config/*, mapping/*, schemas/uniprot/*)
- Рефакторинг всех пайплайнов
- Реорганизация domain layer

**Рекомендация:** ОТКЛОНИТЬ. Слишком масштабное расхождение. Если нужны конкретные изменения — делать заново на текущем main.

---

## 4. Рекомендации: что объединять

### MERGE (3 ветки)

| # | Ветка | Причина |
|---|-------|---------|
| 1 | `bolt/optimize-date-extractor-2826375097710156585` | Чистый merge, конкретная оптимизация DateExtractor (singleton, class vars), +тесты |
| 2 | `bolt-optimize-pubmed-identifiers-9455405533693776821` | Чистый merge, single-pass XML extraction, TypedDict сохранены |
| 3 | `bolt/uniprot-feature-optimization-1706687305301958106` | Merge с конфликтом (1 файл), простой resolve, ~7% speedup |

### CHERRY-PICK (идеи из 2 orphaned веток)

| # | Источник | Что взять |
|---|----------|-----------|
| 4 | `bolt-silver-writer-optimization-4078771543740170219` | Паттерн оптимизации цикла в `silver_writer.py` (итерация по schema.names) |
| 5 | `bolt/gold-writer-optimization-9251521540080561602` | Удаление ColumnOrderer overhead, GoldMetadataBuilder extraction |

### ОТКЛОНИТЬ (22 ветки)

Все остальные 22 ветки — отклонить и удалить. Причины:
- Orphaned история (нет общего предка с main)
- Дублируют оптимизации, уже покрытые рекомендованными ветками
- Слишком масштабные расхождения (100-420+ файлов)
- Худшее качество кода по сравнению с выбранными альтернативами

---

## 5. План объединения

### Этап 1: Прямой merge (без конфликтов)

**Порядок важен** — ветки 1 и 2 не конфликтуют друг с другом.

```bash
# Шаг 1.1: Date Extractor optimization
git checkout main
git merge --no-ff origin/bolt/optimize-date-extractor-2826375097710156585 \
  -m "perf(pubmed): optimize DateExtractor — singleton, class vars, module-level calendar import"

# Шаг 1.2: PubMed Identifier optimization
git merge --no-ff origin/bolt-optimize-pubmed-identifiers-9455405533693776821 \
  -m "perf(pubmed): optimize identifier extraction — single-pass XML, identifier_types.py"
```

**Проверки после каждого merge:**
```bash
pytest tests/unit/application/pipelines/pubmed/ -v
mypy --strict src/bioetl/application/pipelines/pubmed/
```

### Этап 2: Merge с разрешением конфликтов

```bash
# Шаг 2.1: UniProt feature optimization (1 конфликт в features.py)
git merge --no-ff origin/bolt/uniprot-feature-optimization-1706687305301958106 \
  -m "perf(uniprot): optimize feature extraction — pattern pre-normalization, walrus operators"

# При конфликте в features.py — принять изменения из ветки (ours: main, theirs: branch),
# затем вручную проверить корректность walrus operators.
```

**Проверки:**
```bash
pytest tests/unit/application/pipelines/uniprot/ -v
mypy --strict src/bioetl/application/pipelines/uniprot/
```

### Этап 3: Ручной cherry-pick оптимизаций

```bash
# Шаг 3.1: Silver Writer loop optimization
# НЕ merge, а ручное применение паттерна из bolt-silver-writer-optimization-4078771543740170219
# Целевой файл: src/bioetl/infrastructure/storage/silver_writer.py
# Изменение: заменить итерацию по rec.items() на итерацию по schema.names

# Шаг 3.2: Gold Writer cleanup (опционально)
# НЕ merge, а ручное применение идей из bolt/gold-writer-optimization-9251521540080561602
# Целевые файлы: gold_writer.py, batch_writer.py
# Изменение: удаление ColumnOrderer overhead, извлечение GoldMetadataBuilder
```

### Этап 4: Финальная верификация

```bash
# Полный тестовый прогон
pytest --cov=src/bioetl --cov-fail-under=85 -v

# Type checking
mypy --strict src/bioetl/

# Architecture tests
pytest tests/architecture/ -v

# Lint
make lint
```

---

## 6. Ветки к удалению

После завершения плана объединения — удалить все 27 bolt-веток:

```bash
# Merged ветки (3)
git push origin --delete bolt/optimize-date-extractor-2826375097710156585
git push origin --delete bolt-optimize-pubmed-identifiers-9455405533693776821
git push origin --delete bolt/uniprot-feature-optimization-1706687305301958106

# Отклонённые ветки (24)
git push origin --delete \
  bolt/gold-writer-optimization-9251521540080561602 \
  bolt/optimize-batch-writer-gold-8224212234072549004 \
  bolt/optimize-silver-serialization-17048994287352894847 \
  bolt/optimize-silver-writer-13553046753343703003 \
  bolt/optimize-silver-writer-14305130312494082531 \
  bolt/optimize-silver-writer-4539369462564194106 \
  bolt/optimize-silver-writer-5061550331081307667 \
  bolt/optimize-silver-writer-filtering-16275368554400671306 \
  bolt/pubmed-transformer-optimization-1564101723275582547 \
  bolt/silver-writer-optimization-8085015874627325572 \
  bolt-optimize-pubmed-date-3789117081982362004 \
  bolt-optimize-pubmed-date-parsing-8283081052165591821 \
  bolt-optimize-pubmed-identifiers-17563303524360502919 \
  bolt-optimize-silver-writer-2356727444240081857 \
  bolt-optimize-silver-writer-6952166425433176391 \
  bolt-perf-pubmed-date-parsing-12532949572236019825 \
  bolt-perf-pubmed-transformer-date-5922893198129129252 \
  bolt-pubmed-date-extraction-optimization-10719411922497146945 \
  bolt-pubmed-identifier-opt-169219971728294416 \
  bolt-pubmed-optimization-11776621839494351834 \
  bolt-silver-writer-optimization-11154284540065872566 \
  bolt-silver-writer-optimization-4078771543740170219 \
  bolt-silver-writer-optimization-7894939204007800549 \
  bolt-silver-writer-perf-5880266767462610852
```

---

## Приложение: Диаграмма решений

```
27 bolt-веток
├── 5 с общим предком
│   ├── 3 clean merge ─────────► MERGE (этапы 1-2)
│   │   ├── date-extractor ────► Этап 1.1
│   │   ├── identifiers-9455 ──► Этап 1.2
│   │   └── uniprot-features ──► Этап 2.1 (конфликт — resolve)
│   └── 2 с конфликтами ──────► ОТКЛОНИТЬ (дублируют чистые альтернативы)
│       ├── identifiers-17563 ─► Перекрыта identifiers-9455
│       └── identifier-opt ────► Перекрыта identifiers-9455
└── 22 orphaned
    ├── 2 с ценными идеями ───► CHERRY-PICK вручную (этап 3)
    │   ├── silver-writer-4078 ► Паттерн цикла silver_writer.py
    │   └── gold-writer-9251 ──► GoldMetadataBuilder
    └── 20 устаревших ─────────► УДАЛИТЬ
```

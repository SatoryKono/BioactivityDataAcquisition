# Консолидированный план рефакторинга: унификация полей ChEMBL-пайплайнов

*Версия: 1.0.0 | Дата: 2026-02-13*
*Источники: ветка gFEGo (анализ полей), ветка sRnnM (промты + код)*

---

## 1. Резюме анализа

Два независимых аудита выявили одинаковый набор проблем в 4-х ChEMBL-пайплайнах
(Activity, Assay, Target, Molecule). Оба анализа сходятся в диагнозе и различаются
только в приоритизации и глубине охвата.

### 1.1 Что совпадает (консенсус)

| # | Проблема | gFEGo | sRnnM | Severity |
|---|----------|-------|-------|----------|
| 1 | DTO `*_json` суффикс ≠ Entity/Gold | ✅ §4.8 | ✅ §4.1 | MEDIUM |
| 2 | DTO `action_type_parent` ≠ Entity `action_type_parent_type` | — | ✅ §4.6 | HIGH |
| 3 | `taxonomy_id` семантически перегружен (Activity=target, Assay=assay) | ✅ §4.1–4.2 | ✅ §4.2–4.3 | HIGH |
| 4 | Molecule property alias дублирование (property_* + каноническое) | ✅ §4.6 | ✅ §4.4 | MEDIUM |
| 5 | DTO taxonomy поля сохраняют API-имена (tax_id/assay_tax_id/target_tax_id) | ✅ §4.1 | ✅ §4.2 | MEDIUM |
| 6 | DTO-only поля Target (description, dap_id и др.) | — | ✅ §4.5 | LOW |
| 7 | DQ-конфиг molecule использует API-имена вместо Silver | — | ✅ PROMPT-6 | HIGH |
| 8 | Assay filter column_name = assay_chembl_id (API-имя) | — | ✅ PROMPT-7 | LOW |
| 9 | Silver schema Target: `component_id` ≠ Entity `primary_component_id` | — | ✅ PROMPT-10 | MEDIUM |
| 10 | Silver Activity taxonomy_id: тип `string` ≠ `float64` в Assay/Target | — | ✅ PROMPT-14 | MEDIUM |

### 1.2 Расхождения между анализами

| Тема | gFEGo | sRnnM | Консолидированное решение |
|------|-------|-------|--------------------------|
| `assay_pref_name` → `pref_name` | ✅ Рекомендует переименовать | Не поднимает | **Отложить** — не критично, Entity/Gold уже синхронны |
| `organism` naming (bare vs prefixed) | ✅ §4.2 подробно | Не поднимает | **Отложить** — текущая схема корректна: bare в своём пайплайне, prefix при денормализации |
| parent_molecule_id vs hierarchy_parent_chembl_id | ✅ §4.7 | Не поднимает | **Не менять** — разные уровни абстракции (FK vs hierarchy) |

### 1.3 Что уже сделано в sRnnM (код)

Ветка sRnnM содержит **реальные изменения кода**, но они в основном касаются:
- Удаления `# type: ignore[type-var]` комментариев из Pandera schemas
- Удаления `# type: ignore[call-overload]` из validators
- Мелких type-cast исправлений в трансформерах
- **Регрессия**: `action_type_parent_type` → `action_type_parent` (обратное направление!)

**ВАЖНО**: sRnnM ввела регрессию в chembl.py — переименовала `action_type_parent_type`
обратно в `action_type_parent`, что противоречит Entity/Gold convention.
Основной код (main) уже имеет правильное `action_type_parent_type`.

---

## 2. Консолидированный план рефакторинга

### Фаза 0: Исправление регрессии sRnnM (если мержится)

Если изменения sRnnM будут мержиться в main, необходимо **откатить** переименование
`action_type_parent_type` → `action_type_parent` в chembl.py. Main уже содержит
правильное имя.

### Фаза 1: DTO ↔ Entity/Gold синхронизация (независимые, параллельные)

Все промты этой фазы **независимы** и могут выполняться параллельно.

| RF-ID | Задача | Файлы | Blast Radius |
|-------|--------|-------|-------------|
| RF-01 | Убрать `_json` суффикс в DTO Activity | chembl.py, activity_transformer.py | LOW |
| RF-02 | Убрать `_json` суффикс в DTO Assay | chembl.py, assay_transformer.py | LOW |
| RF-03 | Убрать `_json` суффикс в DTO Target | chembl.py, target_transformer.py | LOW |
| RF-04 | Убрать `_json` суффикс в DTO Molecule | chembl.py, molecule_transformer.py | MEDIUM |
| RF-05 | DQ-конфиг molecule → Silver-имена | configs/dq/entities/chembl/molecule.yaml | LOW |
| RF-06 | Assay filter column_name → assay_id | configs/filter/entities/chembl/assay.yaml | LOW |
| RF-07 | Silver Target: component_id → primary_component_id | silver.py, тесты | LOW |

### Фаза 2: Taxonomy семантическая унификация (последовательные)

| RF-ID | Задача | Зависимости | Blast Radius |
|-------|--------|-------------|-------------|
| RF-08 | Activity: taxonomy_id → target_taxonomy_id + тип float64 | — | HIGH |
| RF-09 | Assay: taxonomy_id → assay_taxonomy_id | — | HIGH |
| RF-10 | Документация: обновить field-catalog и naming-matrix | RF-08, RF-09 | LOW |

### Фаза 3: Molecule property унификация (отдельное решение)

| RF-ID | Задача | Описание | Blast Radius |
|-------|--------|----------|-------------|
| RF-11 | Molecule Gold: добавить недостающие alias для property_* | Выбрать стратегию: A) только alias в Gold, B) оба стиля | MEDIUM |

### Фаза 4: Очистка DTO-only полей Target

| RF-ID | Задача | Описание | Blast Radius |
|-------|--------|----------|-------------|
| RF-12 | Решение по DTO-only полям Target | description, dap_id, target_constraints, component_tax_ids | LOW |

### Фаза 5: Финальная валидация

| RF-ID | Задача |
|-------|--------|
| RF-13 | make lint + mypy --strict + pytest tests/architecture/ + coverage ≥85% |

---

## 3. Граф зависимостей

```
Фаза 1 (параллельно):
  RF-01 ─┐
  RF-02 ─┤
  RF-03 ─┤
  RF-04 ─┼─→ Фаза 2:
  RF-05 ─┤     RF-08 ─┐
  RF-06 ─┤     RF-09 ─┼─→ RF-10 ─→ Фаза 5: RF-13
  RF-07 ─┘            │
                      │
         Фаза 3: RF-11 ─┘
         Фаза 4: RF-12 ─┘
```

---

## 4. Набор промтов для модификации кода

### PROMPT RF-01: Убрать суффикс `_json` в DTO Activity

**Severity**: MEDIUM | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В файле `src/bioetl/domain/entities/chembl.py`, класс `ActivityRecord`:
- Переименовать `activity_properties_json` → `activity_properties`

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — поле DTO
2. `src/bioetl/application/pipelines/chembl/activity_transformer.py` — обращения `record.activity_properties_json` → `record.activity_properties`
3. Тесты: все файлы с `activity_properties_json` в `tests/`

**Верификация:**
```bash
grep -rn "activity_properties_json" src/ tests/ --include="*.py"
# Ожидание: 0 совпадений
pytest tests/unit/application/pipelines/ -k activity -v
```

---

### PROMPT RF-02: Убрать суффикс `_json` в DTO Assay

**Severity**: MEDIUM | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В `AssayRecord` (`src/bioetl/domain/entities/chembl.py`):
- `assay_classifications_json` → `assay_classifications`
- `assay_parameters_json` → `assay_parameters`

Примечание: `variant_sequence_json` **НЕ трогать** — это forensic-поле, которое
намеренно хранит исходный JSON варианта параллельно с распакованными полями.

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — 2 поля в `AssayRecord`
2. `src/bioetl/application/pipelines/chembl/assay_transformer.py` — обращения к полям
3. Тесты: `tests/unit/application/pipelines/` (assay-related)

**Верификация:**
```bash
grep -rn "assay_classifications_json\|assay_parameters_json" src/ tests/ --include="*.py"
# Ожидание: 0 совпадений
```

---

### PROMPT RF-03: Убрать суффикс `_json` в DTO Target

**Severity**: MEDIUM | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В `TargetRecord` (`src/bioetl/domain/entities/chembl.py`):
- `target_components_json` → `target_components`
- `target_component_synonyms_json` → `target_component_synonyms`
- `cross_references_json` → `cross_references`

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — 3 поля в `TargetRecord`
2. `src/bioetl/application/pipelines/chembl/target_transformer.py` — обращения
3. Тесты: `tests/` (target-related)

**Верификация:**
```bash
grep -rn "target_components_json\|target_component_synonyms_json" src/ tests/ --include="*.py"
# Ожидание: 0 совпадений (cross_references_json может быть в Molecule — проверить отдельно)
```

---

### PROMPT RF-04: Убрать суффикс `_json` в DTO Molecule

**Severity**: MEDIUM | **Blast radius**: MEDIUM (6 полей) | **Фаза**: 1

**Задание:**

В `MoleculeRecord` (`src/bioetl/domain/entities/chembl.py`):
- `molecule_hierarchy_json` → `molecule_hierarchy`
- `molecule_properties_json` → `molecule_properties`
- `molecule_structures_json` → `molecule_structures`
- `molecule_synonyms_json` → `molecule_synonyms`
- `cross_references_json` → `cross_references`
- `atc_classifications_json` → `atc_classifications`

Также проверить `TargetComponentRecord`:
- `target_component_synonyms_json` → `target_component_synonyms`
- `target_component_xrefs_json` → `target_component_xrefs`
- `protein_classifications_json` → `protein_classifications`

И `CellLineRecord`:
- Проверить наличие `_json` полей и убрать при необходимости.

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — все Record-классы
2. `src/bioetl/application/pipelines/chembl/molecule_transformer.py`
3. `src/bioetl/application/pipelines/chembl/target_component_transformer.py`
4. `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py` — если маппит _json поля
5. Тесты: все molecule/target_component-related

**Верификация:**
```bash
grep -rn "_json" src/bioetl/domain/entities/chembl.py | grep -v "variant_sequence_json\|#"
# Ожидание: 0 совпадений (кроме variant_sequence_json)
```

---

### PROMPT RF-05: DQ-конфиг molecule — Silver-имена

**Severity**: HIGH | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В `configs/dq/entities/chembl/molecule.yaml` DQ-правила ссылаются на API-имена полей
(`full_mwt`, `alogp`), но DQ-движок валидирует Silver-данные, где поля называются
`property_full_mwt`, `property_alogp`.

**Изменения:**

```yaml
# БЫЛО:
- field: full_mwt
- field: alogp

# СТАЛО:
- field: property_full_mwt
- field: property_alogp
```

**Файлы для изменения:**

1. `configs/dq/entities/chembl/molecule.yaml`

**Верификация:**
```bash
grep -n "field:" configs/dq/entities/chembl/molecule.yaml
# Все field-значения должны совпадать с именами в Silver Schema
```

---

### PROMPT RF-06: Assay filter column_name

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В `configs/filter/entities/chembl/assay.yaml` поле `input_filter.column_name` использует
`assay_chembl_id` (API-имя), тогда как все остальные пайплайны используют unified-имена.

**Перед изменением** проверить, что CSV-файл `data/input/assay.csv` (если существует)
использует `assay_id` как заголовок. Если CSV использует `assay_chembl_id` — обновить
и его, или оставить column_name как есть (оно ссылается на CSV-заголовок).

```yaml
# БЫЛО:
input_filter:
  column_name: "assay_chembl_id"
  filter_field: "assay_id"

# СТАЛО (если CSV совместим):
input_filter:
  column_name: "assay_id"
  filter_field: "assay_id"
```

**Файлы для изменения:**

1. `configs/filter/entities/chembl/assay.yaml`
2. `data/input/assay.csv` (если нужно обновить заголовок)

---

### PROMPT RF-07: Silver Target — component_id → primary_component_id

**Severity**: MEDIUM | **Blast radius**: LOW | **Фаза**: 1

**Задание:**

В Silver Schema `CHEMBL_TARGET_SCHEMA` (если существует отдельно от Pandera schema)
поле `component_id` не совпадает с Entity `Target.primary_component_id`.

Проверить файл `src/bioetl/infrastructure/schemas/silver.py` (или аналогичный) и
привести имя к `primary_component_id`.

**Файлы для изменения:**

1. `src/bioetl/infrastructure/schemas/silver.py` (или `src/bioetl/domain/schemas/chembl/target.py`)
2. Тесты Silver-контрактов

**Верификация:**
```bash
grep -n "component_id" src/bioetl/infrastructure/schemas/silver.py | grep -i target
# Ожидание: primary_component_id
```

---

### PROMPT RF-08: Activity taxonomy_id → target_taxonomy_id + тип float64

**Severity**: HIGH | **Blast radius**: HIGH | **Фаза**: 2

**Задание:**

В Activity пайплайне `taxonomy_id` хранит NCBI Taxonomy ID **мишени** (target).
При join с Assay (где `taxonomy_id` = taxonomy организма анализа) возникает
семантическое перекрытие. Переименовать `taxonomy_id` → `target_taxonomy_id`.

Одновременно исправить тип данных: в Activity Silver schema taxonomy_id имеет тип
`string`, тогда как в Assay и Target — `float64` (nullable int pattern).
Привести к единому `float64`.

**Файлы для изменения (в порядке зависимостей):**

1. `src/bioetl/domain/entities/bioactivity.py`:
   - Entity `Bioactivity`: `taxonomy_id` → `target_taxonomy_id`

2. `src/bioetl/domain/contracts/gold/chembl.py`:
   - `ChEMBLActivityGoldSchema`: `taxonomy_id` → `target_taxonomy_id`

3. `src/bioetl/domain/schemas/chembl/activity.py` (Silver Pandera schema):
   - `taxonomy_id: Series[str]` → `target_taxonomy_id: Series[float]`

4. `src/bioetl/application/pipelines/chembl/activity_transformer.py`:
   - Маппинг `target_tax_id` → `target_taxonomy_id` (вместо `taxonomy_id`)
   - Убедиться, что значение конвертируется в float

5. `configs/dq/entities/chembl/activity.yaml` — если есть ссылки на `taxonomy_id`
6. `configs/filter/entities/chembl/activity.yaml` — если есть ссылки на `taxonomy_id`
7. Тесты: activity transformer, silver schema, gold schema, e2e

**Верификация:**
```bash
# Не должно быть bare taxonomy_id в Activity-контексте
grep -rn '"taxonomy_id"' src/bioetl/domain/entities/bioactivity.py \
  src/bioetl/domain/contracts/gold/chembl.py
# Ожидание: 0 совпадений

pytest tests/unit/application/pipelines/ -k activity -v
pytest tests/architecture/ -v
```

---

### PROMPT RF-09: Assay taxonomy_id → assay_taxonomy_id

**Severity**: HIGH | **Blast radius**: HIGH | **Фаза**: 2

**Задание:**

В Assay пайплайне `taxonomy_id` хранит NCBI Taxonomy ID **организма анализа**.
Переименовать `taxonomy_id` → `assay_taxonomy_id` для семантической ясности.

`variant_taxonomy_id` уже имеет контекстный префикс — **не менять**.

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl_activity.py` (или где определён Assay entity):
   - `taxonomy_id` → `assay_taxonomy_id`

2. `src/bioetl/domain/contracts/gold/chembl.py`:
   - `ChEMBLAssayGoldSchema`: `taxonomy_id` → `assay_taxonomy_id`

3. `src/bioetl/domain/schemas/chembl/assay.py` (Silver Pandera schema):
   - `taxonomy_id` → `assay_taxonomy_id`

4. `src/bioetl/application/pipelines/chembl/assay_transformer.py`:
   - Маппинг `assay_tax_id` → `assay_taxonomy_id`

5. Тесты: assay transformer, silver schema, gold schema

**Верификация:**
```bash
# В Assay entity/schema не должно быть bare taxonomy_id
grep -n "taxonomy_id" src/bioetl/domain/entities/chembl_activity.py
# Ожидание: assay_taxonomy_id, variant_taxonomy_id (но НЕ bare taxonomy_id)
```

---

### PROMPT RF-10: Обновление документации

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 2 (после RF-08, RF-09)

**Задание:**

Обновить документацию полей для отражения переименований taxonomy:

1. `docs/03-data-model/field-catalog-source-pipelines.md`:
   - Секция chembl_activity: `taxonomy_id` → `target_taxonomy_id`
   - Секция chembl_assay: `taxonomy_id` → `assay_taxonomy_id`

2. `docs/03-data-model/field-naming-unification-matrix.md`:
   - Обновить секцию таксономии

---

### PROMPT RF-11: Molecule property alias — унификация Gold

**Severity**: MEDIUM | **Blast radius**: MEDIUM | **Фаза**: 3

**Задание:**

В Molecule Gold Schema часть `property_*` полей имеет каноническое alias-имя,
а часть — нет. Это создаёт непоследовательность.

**Два варианта (выбрать один):**

**Вариант A (рекомендуется): Только alias-имена в Gold**

Удалить `property_*` из Gold, оставить только канонические:
- `property_ro5_violations` → `ro5_violation_count`
- `property_qed_weighted` → `qed_score`
- `property_full_molformula` → `molecular_formula`
- `property_ro3_pass` → `ro3_pass`
- `property_mw_freebase` → `mw_freebase`

**Вариант B: Оставить оба стиля, добавить alias для остатков**

Добавить alias-поля для `property_*`, у которых их нет, сохранив и `property_*` версии.

**Файлы для изменения (Вариант A):**

1. `src/bioetl/domain/entities/chembl_structures.py` — Molecule entity: добавить alias-атрибуты
2. `src/bioetl/application/pipelines/chembl/molecule_transformer.py` — вычисление alias-полей
3. `src/bioetl/domain/contracts/gold/chembl.py` — Gold schema: заменить property_* на alias
4. Тесты: gold schema, molecule transformer, e2e

---

### PROMPT RF-12: Решение по DTO-only полям Target

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 4

**Задание:**

В `TargetRecord` (DTO) есть поля, отсутствующие в Entity/Gold:
- `description` — описание мишени
- `dap_id` — Drug-Affinity Panel ID
- `target_constraints` — ограничения мишени
- `component_tax_ids` — taxonomy IDs компонентов

Для каждого поля принять решение:

| DTO Field | Рекомендация | Обоснование |
|-----------|-------------|-------------|
| `description` | **Добавить в Entity/Silver/Gold** | Полезно для поиска и аннотации |
| `dap_id` | **Удалить из DTO** | Не используется downstream |
| `target_constraints` | **Удалить из DTO** | Не используется downstream |
| `component_tax_ids` | **Удалить из DTO** | Дублирует данные из component flattening |

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — `TargetRecord`
2. (опционально) Entity Target, Silver Schema, Gold Schema — если добавляем description

---

### PROMPT RF-13: Финальная валидация

**Severity**: CRITICAL | **Blast radius**: — | **Фаза**: 5

**Задание:**

После выполнения всех предыдущих промтов запустить полную верификацию:

```bash
# 1. Linting
make lint

# 2. Type checking
mypy --strict src/bioetl/

# 3. Architecture tests
pytest tests/architecture/ -v

# 4. Silver/Gold schema consistency
pytest tests/unit/infrastructure/schemas/ -v

# 5. Transformer tests
pytest tests/unit/application/pipelines/ -v

# 6. E2E tests
pytest tests/e2e/ -v --timeout=120

# 7. Coverage
pytest --cov=src/bioetl --cov-fail-under=85
```

**Остаточные расхождения — grep-проверка:**
```bash
# _json в DTO (кроме variant_sequence_json)
grep -rn "_json" src/bioetl/domain/entities/chembl.py | grep -v variant_sequence_json | grep -v "#"

# bare taxonomy_id в Activity/Assay
grep -rn '"taxonomy_id"' src/bioetl/domain/entities/bioactivity.py \
  src/bioetl/domain/contracts/gold/chembl.py

# action_type_parent без _type
grep -rn "action_type_parent[^_]" src/ --include="*.py"

# component_id вместо primary_component_id в Silver
grep -rn '"component_id"' src/bioetl/infrastructure/ --include="*.py"
```

---

## 5. Матрица затронутых файлов

| Файл | RF-01 | RF-02 | RF-03 | RF-04 | RF-05 | RF-06 | RF-07 | RF-08 | RF-09 | RF-10 | RF-11 | RF-12 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| domain/entities/chembl.py | ✏️ | ✏️ | ✏️ | ✏️ | | | | | | | | ✏️ |
| domain/entities/bioactivity.py | | | | | | | | ✏️ | | | | |
| domain/entities/chembl_activity.py | | | | | | | | | ✏️ | | | |
| domain/entities/chembl_structures.py | | | | | | | | | | | ✏️ | |
| domain/contracts/gold/chembl.py | | | | | | | | ✏️ | ✏️ | | ✏️ | |
| domain/schemas/chembl/*.py | | | | | | | | ✏️ | ✏️ | | | |
| infrastructure/schemas/silver.py | | | | | | | ✏️ | ✏️ | | | | |
| application/pipelines/chembl/activity_transformer.py | ✏️ | | | | | | | ✏️ | | | | |
| application/pipelines/chembl/assay_transformer.py | | ✏️ | | | | | | | ✏️ | | | |
| application/pipelines/chembl/target_transformer.py | | | ✏️ | | | | | | | | | |
| application/pipelines/chembl/molecule_transformer.py | | | | ✏️ | | | | | | | ✏️ | |
| configs/dq/entities/chembl/molecule.yaml | | | | | ✏️ | | | | | | | |
| configs/filter/entities/chembl/assay.yaml | | | | | | ✏️ | | | | | | |
| docs/03-data-model/field-catalog-*.md | | | | | | | | | | ✏️ | | |

---

## 6. Правила для всех промтов

1. **Каждое изменение** сопровождается обновлением тестов.
2. **После каждого промта**: `make lint && pytest tests/architecture/ -v`.
3. **Не менять API/Bronze имена** — они определяются внешним API ChEMBL.
4. **DTO → Entity маппинг** происходит в Transformer.
5. **Коммитить каждый промт отдельно** с описательным сообщением: `refactor(fields): RF-XX — <описание>`.
6. **variant_sequence_json НЕ трогать** — forensic-поле, хранящее исходный JSON.
7. При переименовании полей в Pandera schemas — проверить VCR cassettes и snapshot-тесты.

---

## 7. Оценка рисков

| RF-ID | Риск | Митигация |
|-------|------|-----------|
| RF-01..04 | Сломать десериализацию из Bronze | grep `_json` во всех адаптерах и entity_mapper |
| RF-08, RF-09 | Сломать Delta Lake merge (column mismatch) | Требуется REBUILD после применения |
| RF-08, RF-09 | Сломать downstream consumers Gold-данных | Обновить все downstream перед применением |
| RF-11 | Потерять обратную совместимость Gold | Применять с осторожностью, тегировать версию схемы |
| RF-05 | DQ-правила перестанут работать если поля не совпадут | Сверить с реальной Silver-схемой перед коммитом |

---

## 8. Порядок выполнения

```
Неделя 1:  RF-01, RF-02, RF-03, RF-04 (параллельно) + RF-05, RF-06, RF-07
Неделя 2:  RF-08 + RF-09 (последовательно, с прогоном тестов после каждого)
           RF-10 (документация)
Неделя 3:  RF-11 (molecule aliases — требует дизайн-решения)
           RF-12 (DTO-only поля — требует продуктового решения)
Финал:     RF-13 (полная валидация)
```

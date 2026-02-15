# Консолидированный план рефакторинга: унификация полей ChEMBL-пайплайнов

*Версия: 2.0.0 | Дата: 2026-02-15*
*Источники: ветка gFEGo (анализ полей), ветка sRnnM (промты + код), ветка 7Zhjk (filtering config)*
*Синхронизировано с main на 2026-02-15 (commit 2c360d5)*

---

## 1. Резюме анализа

Три независимых аудита выявили набор проблем в ChEMBL-пайплайнах
(Activity, Assay, Target, Molecule). Значительная часть проблем уже исправлена
в main — этот документ отражает **актуальное состояние** кодовой базы.

### 1.1 Статус исправлений (синхронизировано с main)

| # | Проблема | Статус | Где исправлено |
|---|----------|--------|----------------|
| 1 | DTO `*_json` суффикс ≠ Entity/Gold | ✅ DONE | Все `_json` удалены кроме forensic (`variant_sequence_json`, `features_json`) |
| 2 | `action_type_parent` ≠ `action_type_parent_type` | ✅ DONE | Main содержит правильное `action_type_parent_type` |
| 3 | `taxonomy_id` перегружен (Activity/Assay) | ✅ DONE | Activity→`target_taxonomy_id`, Assay→`assay_taxonomy_id` |
| 4 | Taxonomy тип `string` ≠ `float64` | ✅ DONE | Все taxonomy поля — `float64` (nullable int pattern) |
| 5 | DTO taxonomy поля с API-именами | ✅ DONE | Трансформеры маппят `target_tax_id`→`target_taxonomy_id`, `assay_tax_id`→`assay_taxonomy_id` |
| 6 | Filtering config рефакторинг | ✅ DONE | PR #2122: SilverFilterConfig, BaseConfigLoader, dq_overrides |
| 7 | DQ-конфиг molecule: entity-level | ✅ DONE | `configs/dq/entities/chembl/molecule.yaml` использует `property_full_mwt`, `property_alogp` |
| 8 | DQ-конфиг molecule: pipeline inline | ⚠️ PENDING | `configs/pipelines/chembl/molecule.yaml` ещё использует `full_mwt`, `alogp` |
| 9 | Assay filter `column_name = assay_chembl_id` | ⚠️ PENDING | `configs/filter/entities/chembl/assay.yaml` |
| 10 | Molecule property alias дублирование | ⚠️ PENDING | Gold schema имеет и `property_*` и канонические имена |
| 11 | DTO-only поля Target | ⚠️ PENDING | `description` уже в Entity, остальные требуют решения |
| 12 | Pipeline inline DQ: `_normalize_source_config` complexity | ⚠️ PENDING | 147 LOC, CC>15 (рекомендация FIX-7 из codex audit) |

### 1.2 Что НЕ нужно менять

| Тема | Обоснование |
|------|-------------|
| `assay_pref_name` → `pref_name` | Entity/Gold уже синхронны, не критично |
| `organism` bare vs prefixed | Корректно: bare в своём пайплайне, prefix при денормализации |
| `parent_molecule_id` vs `hierarchy_parent_chembl_id` | Разные уровни абстракции (FK vs hierarchy) |
| Target/TargetComponent `taxonomy_id` (bare) | Нет семантической перегрузки — в Target контексте однозначно |
| `variant_sequence_json` | Forensic-поле, намеренно хранит исходный JSON |
| `features_json` (UniProt) | Forensic-поле, аналогично |

---

## 2. Актуальный план рефакторинга

### Фаза 1: Config-уровень синхронизация (независимые, параллельные)

| RF-ID | Задача | Файлы | Blast Radius |
|-------|--------|-------|-------------|
| RF-01 | Pipeline inline DQ molecule → Silver-имена | `configs/pipelines/chembl/molecule.yaml` | LOW |
| RF-02 | Assay filter `column_name` → unified name | `configs/filter/entities/chembl/assay.yaml` | LOW |

### Фаза 2: Molecule property унификация (дизайн-решение)

| RF-ID | Задача | Описание | Blast Radius |
|-------|--------|----------|-------------|
| RF-03 | Molecule Gold: унифицировать property_* alias | Выбрать стратегию: A) только alias в Gold, B) оба стиля | MEDIUM |

### Фаза 3: DTO-only поля Target (продуктовое решение)

| RF-ID | Задача | Описание | Blast Radius |
|-------|--------|----------|-------------|
| RF-04 | Решение по DTO-only полям Target | dap_id, target_constraints, component_tax_ids | LOW |

### Фаза 4: Техдолг (отдельный PR)

| RF-ID | Задача | Описание | Blast Radius |
|-------|--------|----------|-------------|
| RF-05 | Декомпозиция `_normalize_source_config` | 147 LOC, CC>15 → разбить на 3-4 функции | MEDIUM |

### Фаза 5: Документация и финальная валидация

| RF-ID | Задача |
|-------|--------|
| RF-06 | Обновить field-catalog и naming-matrix (отразить taxonomy переименования) |
| RF-07 | `make lint` + `mypy --strict` + `pytest tests/architecture/` + coverage ≥85% |

---

## 3. Граф зависимостей

```
Фаза 1 (параллельно):
  RF-01 ─┐
  RF-02 ─┼─→ Фаза 5: RF-06 ─→ RF-07
         │
Фаза 2: RF-03 ─┘
Фаза 3: RF-04 ─┘
Фаза 4: RF-05 (независимый PR)
```

---

## 4. Набор промтов для модификации кода

### PROMPT RF-01: Pipeline inline DQ molecule — Silver-имена

**Severity**: HIGH | **Blast radius**: LOW | **Фаза**: 1

**Контекст:**

Entity-level DQ конфиг (`configs/dq/entities/chembl/molecule.yaml`) уже использует
правильные Silver-имена (`property_full_mwt`, `property_alogp`). Но **pipeline inline
DQ overrides** в `configs/pipelines/chembl/molecule.yaml` всё ещё ссылаются на
API-имена (`full_mwt`, `alogp`, `hba`, `hbd`, `psa`).

DQ-движок валидирует Silver-данные, где поля трансформированы. Все `field:` значения
в `dq_rules.field_validations` должны совпадать с именами в Silver Schema
(`src/bioetl/infrastructure/schemas/silver.py`, строки 650-680).

**Задание:**

В `configs/pipelines/chembl/molecule.yaml`, секция `dq_rules.field_validations`:

```yaml
# БЫЛО:
- field: "full_mwt"
- field: "alogp"
- field: "canonical_smiles"
- field: "hba"
- field: "hbd"
- field: "psa"

# СТАЛО:
- field: "property_full_mwt"
- field: "property_alogp"
- field: "canonical_smiles"    # ← без изменения, уже Silver-имя
- field: "property_hba"
- field: "property_hbd"
- field: "property_psa"
```

Также проверить `cross_field_validations`:
```yaml
# Проверить, что canonical_smiles, standard_inchi, standard_inchi_key
# совпадают с Silver Schema именами
```

**Файлы для изменения:**

1. `configs/pipelines/chembl/molecule.yaml` — секция `dq_rules`

**Верификация:**
```bash
# Все field-значения в inline DQ должны совпадать с Silver Schema
grep -A1 "field:" configs/pipelines/chembl/molecule.yaml | grep '"' | \
  while read -r line; do
    field=$(echo "$line" | grep -oP '"\K[^"]+')
    grep -q "\"$field\"" src/bioetl/infrastructure/schemas/silver.py || echo "MISMATCH: $field"
  done

# Перед изменением — проверить Silver Schema molecule fields
grep "pa.field" src/bioetl/infrastructure/schemas/silver.py | grep -i "mwt\|alogp\|hba\|hbd\|psa"
```

---

### PROMPT RF-02: Assay filter column_name

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 1

**Контекст:**

В `configs/filter/entities/chembl/assay.yaml` поле `input_filter.column_name` использует
`assay_chembl_id` (API-имя), тогда как остальные пайплайны используют unified-имена.

`column_name` ссылается на заголовок CSV-файла с ID для фильтрации (`data/input/assay.csv`).
`filter_field` ссылается на поле API-запроса ChEMBL.

**Задание:**

**Перед изменением** проверить:
1. Существует ли `data/input/assay.csv`?
2. Какой заголовок использует CSV (`assay_chembl_id` или `assay_id`)?
3. Используется ли `column_name` в коде input-фильтрации?

```yaml
# Текущее состояние:
input_filter:
  column_name: "assay_chembl_id"
  filter_field: "assay_id"

# Если CSV использует assay_id:
input_filter:
  column_name: "assay_id"
  filter_field: "assay_id"

# Если CSV использует assay_chembl_id — оставить как есть (column_name = CSV header)
```

**Файлы для изменения:**

1. `configs/filter/entities/chembl/assay.yaml`
2. `data/input/assay.csv` (если нужно обновить заголовок)

**Верификация:**
```bash
# Проверить другие пайплайны для паттерна column_name vs filter_field
grep -A2 "column_name" configs/filter/entities/chembl/*.yaml
```

---

### PROMPT RF-03: Molecule property alias — унификация Gold

**Severity**: MEDIUM | **Blast radius**: MEDIUM | **Фаза**: 2

**Контекст:**

В Molecule Gold Schema часть `property_*` полей имеет каноническое alias-имя,
а часть — нет. Это создаёт непоследовательность для downstream consumers.

Текущее состояние (проверить в `src/bioetl/domain/contracts/gold/chembl.py`):
- Часть полей: `property_full_mwt` + alias `molecular_weight`
- Часть полей: только `property_*` без alias

**Задание:**

**Два варианта (выбрать один):**

**Вариант A (рекомендуется): Только alias-имена в Gold**

В Gold Schema удалить `property_*` столбцы, оставить только канонические:
- `property_ro5_violations` → `ro5_violation_count`
- `property_qed_weighted` → `qed_score`
- `property_full_molformula` → `molecular_formula`
- `property_ro3_pass` → `ro3_pass`
- `property_mw_freebase` → `mw_freebase`

**Вариант B: Оставить оба стиля, добавить alias для остатков**

Добавить alias-поля для `property_*`, у которых их нет, сохранив и `property_*` версии.

**Файлы для изменения (Вариант A):**

1. `src/bioetl/domain/contracts/gold/chembl.py` — Gold schema: заменить `property_*` на alias
2. `src/bioetl/application/pipelines/chembl/molecule_transformer.py` — вычисление alias-полей
3. `src/bioetl/domain/entities/chembl_structures.py` — Molecule entity: добавить alias-атрибуты (если нужно)
4. Тесты: gold schema, molecule transformer

**Верификация:**
```bash
# После изменения: Gold schema не должна содержать property_* (кроме тех, что = Silver имя)
grep "property_" src/bioetl/domain/contracts/gold/chembl.py | grep -i molecule

pytest tests/unit/application/pipelines/ -k molecule -v
pytest tests/architecture/ -v
```

---

### PROMPT RF-04: Решение по DTO-only полям Target

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 3

**Контекст:**

В `TargetRecord` (DTO, `src/bioetl/domain/entities/chembl.py`) есть поля, отсутствующие
в Entity/Gold. Поле `description` **уже добавлено** в Entity
(`src/bioetl/domain/entities/chembl_structures.py:109`).

**Задание:**

Для оставшихся DTO-only полей принять решение:

| DTO Field | Рекомендация | Обоснование |
|-----------|-------------|-------------|
| `description` | ✅ DONE | Уже в Entity (`chembl_structures.py:109`) |
| `dap_id` | **Удалить из DTO** | Не используется downstream |
| `target_constraints` | **Удалить из DTO** | Не используется downstream |
| `component_tax_ids` | **Удалить из DTO** | Дублирует данные из component flattening |

**Файлы для изменения:**

1. `src/bioetl/domain/entities/chembl.py` — удалить неиспользуемые поля из `TargetRecord`
2. `src/bioetl/application/pipelines/chembl/target_transformer.py` — убрать маппинг удалённых полей
3. `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py` — убрать маппинг, если есть
4. Тесты: target transformer

**Верификация:**
```bash
grep -rn "dap_id\|target_constraints\|component_tax_ids" src/ tests/ --include="*.py"
# Ожидание: 0 совпадений (или только в коментариях)

pytest tests/unit/application/pipelines/ -k target -v
```

---

### PROMPT RF-05: Декомпозиция `_normalize_source_config`

**Severity**: MEDIUM | **Blast radius**: MEDIUM | **Фаза**: 4

**Контекст:**

Функция `_normalize_source_config` в `src/bioetl/infrastructure/config_loader.py`
(строки ~253-399) имеет 147 LOC и CC>15. Рекомендация FIX-7 из аудита
`docs/audit/codex-filtering-fix-prompts.md`.

**Задание:**

Разбить `_normalize_source_config` на 3-4 функции с чёткой ответственностью:

1. `_normalize_source_endpoints()` — обработка endpoints/URL конфигурации
2. `_normalize_source_auth()` — обработка аутентификации
3. `_normalize_source_pagination()` — обработка пагинации
4. `_normalize_source_rate_limits()` — обработка rate limiting

**Файлы для изменения:**

1. `src/bioetl/infrastructure/config_loader.py` — рефакторинг `_normalize_source_config`
2. Тесты: `tests/unit/infrastructure/test_config.py`, `tests/unit/infrastructure/test_config_dynamic.py`

**Верификация:**
```bash
# Проверить CC после рефакторинга
ruff check src/bioetl/infrastructure/config_loader.py --select C901

pytest tests/unit/infrastructure/ -k config -v
```

---

### PROMPT RF-06: Обновление документации полей

**Severity**: LOW | **Blast radius**: LOW | **Фаза**: 5

**Задание:**

Обновить документацию для отражения **уже выполненных** переименований taxonomy:

1. `docs/03-data-model/field-catalog-source-pipelines.md`:
   - Секция chembl_activity: `taxonomy_id` → `target_taxonomy_id` (тип: `float64`)
   - Секция chembl_assay: `taxonomy_id` → `assay_taxonomy_id` (тип: `float64`)

2. `docs/03-data-model/field-naming-unification-matrix.md`:
   - Обновить секцию таксономии
   - Добавить строку `_json` suffix removal (✅ завершено)

3. `docs/03-data-model/field-migration-checklist.md`:
   - Отметить завершённые миграции

**Верификация:**
```bash
# Документация не должна ссылаться на устаревшие имена
grep -n "taxonomy_id" docs/03-data-model/field-catalog-source-pipelines.md | \
  grep -v "target_taxonomy_id\|assay_taxonomy_id\|variant_taxonomy_id\|cell_source_taxonomy_id"
```

---

### PROMPT RF-07: Финальная валидация

**Severity**: CRITICAL | **Blast radius**: — | **Фаза**: 5

**Задание:**

После выполнения всех предыдущих промтов запустить полную верификацию:

```bash
# 1. Linting
ruff check src/ tests/
ruff format --check src/ tests/

# 2. Type checking
mypy --config-file pyproject.toml src/bioetl/

# 3. Architecture tests
pytest tests/architecture/ -v

# 4. Silver/Gold schema consistency
pytest tests/unit/infrastructure/schemas/ -v

# 5. Transformer tests
pytest tests/unit/application/pipelines/ -v

# 6. Full test suite
pytest tests/ -m "not e2e and not benchmark" --ignore=tests/e2e --ignore=tests/contract -q

# 7. Coverage
pytest --cov=src/bioetl --cov-fail-under=85
```

**Остаточные расхождения — grep-проверка:**
```bash
# _json в DTO (кроме forensic-полей)
grep -rn "_json" src/bioetl/domain/entities/chembl.py | \
  grep -v "variant_sequence_json\|features_json\|#\|serialize_to_json"

# bare taxonomy_id в Activity/Assay (ожидание: 0)
grep -rn '"taxonomy_id"' src/bioetl/domain/entities/bioactivity.py \
  src/bioetl/domain/contracts/gold/chembl.py

# action_type_parent без _type (ожидание: 0)
grep -rn "action_type_parent[^_]" src/ --include="*.py"

# DQ field names vs Silver Schema (ожидание: все совпадают)
grep "field:" configs/pipelines/chembl/molecule.yaml | grep -v "#"
```

---

## 5. Матрица затронутых файлов

| Файл | RF-01 | RF-02 | RF-03 | RF-04 | RF-05 | RF-06 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| configs/pipelines/chembl/molecule.yaml | ✏️ | | | | | |
| configs/filter/entities/chembl/assay.yaml | | ✏️ | | | | |
| domain/contracts/gold/chembl.py | | | ✏️ | | | |
| domain/entities/chembl.py | | | | ✏️ | | |
| domain/entities/chembl_structures.py | | | ✏️ | | | |
| application/pipelines/chembl/molecule_transformer.py | | | ✏️ | | | |
| application/pipelines/chembl/target_transformer.py | | | | ✏️ | | |
| infrastructure/config_loader.py | | | | | ✏️ | |
| docs/03-data-model/field-catalog-*.md | | | | | | ✏️ |
| docs/03-data-model/field-naming-*.md | | | | | | ✏️ |

---

## 6. Правила для всех промтов

1. **Каждое изменение** сопровождается обновлением тестов.
2. **После каждого промта**: `ruff check src/ tests/ && pytest tests/architecture/ -v`.
3. **Не менять API/Bronze имена** — они определяются внешним API ChEMBL.
4. **DTO → Entity маппинг** происходит в Transformer.
5. **Коммитить каждый промт отдельно**: `refactor(fields): RF-XX — <описание>`.
6. **Forensic `_json` поля НЕ трогать** — `variant_sequence_json`, `features_json`.
7. При переименовании полей в Pandera schemas — проверить VCR cassettes и snapshot-тесты.
8. Pipeline inline DQ `field:` значения **MUST** совпадать с Silver Schema именами.

---

## 7. Оценка рисков

| RF-ID | Риск | Митигация |
|-------|------|-----------|
| RF-01 | DQ-правила перестанут работать если поля не совпадут | Сверить каждое поле с Silver Schema перед коммитом |
| RF-02 | Сломать input-фильтрацию если CSV-заголовок другой | Проверить CSV перед изменением |
| RF-03 | Потерять обратную совместимость Gold | Применять с осторожностью, тегировать версию схемы |
| RF-04 | Сломать десериализацию если поле используется в адаптере | grep перед удалением |
| RF-05 | Регрессия при рефакторинге длинной функции | 100% test coverage для config_loader |

---

## 8. Порядок выполнения

```
Этап 1:  RF-01, RF-02 (параллельно, low risk)
Этап 2:  RF-03 (molecule aliases — требует дизайн-решения)
Этап 3:  RF-04 (DTO-only поля — требует продуктового решения)
Этап 4:  RF-05 (техдолг — отдельный PR)
Финал:   RF-06 (документация) + RF-07 (полная валидация)
```

---

## Appendix A: Завершённые рефакторинги (для справки)

Следующие задачи из v1.0.0 плана **уже выполнены** в main:

| Старый ID | Описание | Коммит/PR |
|-----------|----------|-----------|
| RF-01..04 (v1) | Убрать `_json` суффикс в DTO Activity/Assay/Target/Molecule | Уже в main |
| RF-05 (v1) | DQ entity-level конфиг molecule → Silver-имена | Уже в main |
| RF-08 (v1) | Activity: `taxonomy_id` → `target_taxonomy_id` + float64 | Уже в main |
| RF-09 (v1) | Assay: `taxonomy_id` → `assay_taxonomy_id` | Уже в main |
| — | SilverFilterConfig nominal type separation | PR #2122 |
| — | BaseConfigLoader abstraction | PR #2122 |
| — | `dq_rules` → `dq_overrides` rename (backward-compatible) | PR #2122 |
| — | Directory fallback (filters/filter, quality/dq) | PR #2122 |

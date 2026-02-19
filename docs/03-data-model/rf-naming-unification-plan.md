# RF-NAMING: План унификации наименований полей

*Версия: 2.1.0 | Дата: 2026-02-11 | Обновлено с учётом main (3ba7aea)*

**Новые артефакты:** 
- `docs/03-data-model/field-catalog-source-pipelines.md` — полный каталог бизнес-полей source-пайплайнов.
- `docs/03-data-model/field-naming-unification-matrix.md` — матрица расхождений и целевая номенклатура.
- `docs/03-data-model/field-migration-checklist.md` — поэтапный план внедрения и проверок.

---

## Промты для модификации кода (без обратной совместимости)

Использовать при выполнении миграции: оставляем только канонические имена, legacy-колонки не сохраняем.

**Промт: единое имя поля**
```
Задача: переименовать поле {old-name} в {new-name} в пайплайне {pipeline} без сохранения старого имени.
Контекст:
- Привести трансформер и Pandera схемы (silver/gold) к {new-name};
- Перед записью Silver/Gold — валидировать против Pandera-схемы; при ошибке запись не выполнять;
- Обновить data-schema, DQ, composite field-groups под {new-name};
- Обновить join/field-groups/configs в composite; выполнить REBUILD затронутых таблиц;
- Обновить mapping/field-groups, если используют {old-name}.
Требования:
- Тип и nullability сохранить;
- Порядок колонок по RULES.md §2.9.4 (Column order) + стабильная сортировка строк по бизнес-ключам;
- Тесты: обновить/добавить golden/unit на новый набор колонок; убедиться, что повторный прогон даёт бит-в-бит идентичный результат;
- Удалить упоминания {old-name} в коде и документации.

Полный список переименований (без обратной совместимости):
- publication ids: `doi`→`publication-doi`, `pmid`→`publication-pmid`, `pmc-id`→`publication-pmc-id`, `document-chembl-id`/`paper-id`/`openalex-id`→`publication-id`.
- publication контекст: `document-year`→`publication-year`, `document-journal`→`journal`.
- taxonomy: `target-taxonomy-id`/`assay-taxonomy-id`/`variant-taxonomy-id`/`cell-source-taxonomy-id`/`organism-id`→`taxonomy-id` (float, nullable int pattern).
- activity action: `action-type-action-type`→`action-type`.
- molecule ids: `molecule-chembl-id`/`cid`→`molecule-id`.
- molecule структуры: `structure-standard-inchi-key`→`inchi-key`.
- molecule компоненты: `component-id`→`primary-component-id`.
- молекулярные свойства:
  - `property-full-mwt`→`molecular-weight`;
  - `property-alogp`/`xlogp`→`logp` (+`logp-method`);
  - `property-psa`/`tpsa`→`polar-surface-area`;
  - `property-rtb`→`rotatable-bond-count`;
  - `property-heavy-atoms`→`heavy-atom-count`;
  - `property-aromatic-rings`→`aromatic-ring-count`;
  - `property-hba`→`hba-count`; `property-hbd`→`hbd-count`.
```

**Промт: нормализация таксономии**
```
Цель: унифицировать taxonomy поля в {pipelines} к `taxonomy-id:int64`.
Шаги:
- В трансформерах конвертировать все варианты ({variants}) → taxonomy-id:int64;
- В схемах заменить поля на taxonomy-id:int64;
- Обновить все join/lookup на taxonomy-id;
- Удалить legacy поля {legacy-fields};
- Обновить DQ (валидировать положительное int) и data-schema.
```

**Промт: молекулярные свойства**
```
Цель: унифицировать свойства к канону:
- molecular-weight (float64) — alias property-full-mwt/molecular-weight;
- logp (float64) + logp-method (string: alogp|xlogp);
- polar-surface-area (float64) — alias property-psa/tpsa.
Действия:
- В трансформерах: rename + derive logp-method;
- В схемах: оставить только канон, удалить legacy;
- В документации/field-groups обновить имена;
- Тесты: golden по колонкам и типам.
```

**Промт: публикационные идентификаторы**
```
Цель: привести ключи публикаций к канону:
- publication-id (provider PK);
- publication-doi, publication-pmid, publication-pmc-id.
Шаги:
- В трансформерах: map provider PK → publication-id, убрать document-* и paper-id/openalex-id;
- В схемах: оставить только canonical поля;
- В composite/pipelines: обновить join-ключи;
- Тесты: golden + валидация на уникальность publication-id.
```

---

## 0. Контекст: Publication Unification Precedent

На main уже существует полноценная **экосистема Publication-пайплайнов** (5 провайдеров:
ChEMBL, CrossRef, OpenAlex, PubMed, Semantic Scholar), в которой cross-provider
field naming **уже решён** через:

1. **`PublicationBaseSchema`** (`domain/schemas/common/publication-base.py`) —
   общая base-схема с unified field names
2. **`PUBLICATION-FIELD-MAPPING`** (`domain/mapping/publication-fields.py`) —
   bidirectional маппинг provider → unified names
3. **`apply-field-mapping()`** — runtime rename при трансформации
4. **ADR-030** (archived) — Publication Field Naming Unification decision record

Ключевые унифицированные имена publication:

| Provider name | Unified name | Провайдеры |
|---------------|--------------|------------|
| `year` | `publication-year` | All 5 |
| `citation-count` | `citations-received` | CrossRef, OpenAlex, S2 |
| `reference-count` | `citations-made` | CrossRef, OpenAlex, S2 |
| `first-page` / `last-page` | `page-first` / `page-last` | CrossRef, OpenAlex, PubMed |
| `doc-type` / `source-type` | `publication-type` | ChEMBL, CrossRef, OpenAlex |
| `is-open-access` | `is-oa` | All |
| `affiliations` | `affiliation-list` | OpenAlex, PubMed |

**Вывод для core pipelines:** Паттерн `BaseSchema` + `FIELD-MAPPING` dict + `apply-field-mapping()`
является проверенным подходом и должен быть переиспользован для унификации
Molecule cross-provider naming (N-06).

---

## 1. Обнаруженные проблемы

### 1.1 Инвентаризация несоответствий

Всего выявлено **10 категорий** несоответствий, затрагивающих **~30 полей** в 4 основных,
6 вспомогательных и 5 publication-пайплайнах.

| # | Severity | Категория | Пример |
|---|----------|-----------|--------|
| N-01 | CRITICAL | Type mismatch: `taxonomy-id` | Activity: `str`, все остальные: `float` |
| N-02 | CRITICAL | Type mismatch: `cell-source-taxonomy-id` | Silver: `int`, Gold: `float` |
| N-03 | HIGH | Redundant prefix: `action-type-action-type` | Двойной префикс при flatten |
| N-04 | HIGH | Inconsistent context naming: `pref-name` | Target: `pref-name`, Activity: `target-pref-name`, Assay Composite: `tissue-pref-name` |
| N-05 | HIGH | Inconsistent context naming: `description` | Assay: `description`, Activity: `assay-description` |
| N-06 | MEDIUM | Cross-provider naming: physicochemical properties | ChEMBL: `property-alogp`, PubChem: `xlogp` |
| N-07 | MEDIUM | Inconsistent flatten prefixes | `property-*`, `hierarchy-*`, `ligand-efficiency-*`, но `canonical-smiles` без prefix |
| N-08 | LOW | Singular/plural ambiguity | `component-id` (scalar) vs `component-ids` (list) |
| N-09 | LOW | InChI Key dual naming | `structure-standard-inchi-key` (top-level alias) vs `inchi-key` (flattened) |
| N-10 | HIGH | Publication ↔ Activity context naming gap | Activity: `document-year`, Publication unified: `publication-year`; Activity: `document-journal`, Publication: `journal` |

---

## 2. Детальный анализ каждой проблемы

### N-01: `taxonomy-id` — type mismatch (CRITICAL)

**Проблема:** Одни и те же данные (NCBI Taxonomy ID) имеют разные типы.

| Пайплайн | Поле | Silver тип | Gold тип | Converter |
|----------|------|------------|----------|-----------|
| Activity | `target-taxonomy-id` | `str` | `str` | `validate-taxonomy-id-str` |
| Assay | `assay-taxonomy-id` | `float` | `float` | `validate-taxonomy-id` |
| Assay | `variant-taxonomy-id` | `float` | `float` | `validate-taxonomy-id` |
| Target | `taxonomy-id` | `float` | `float` | `TaxonomyId.from-raw()` |
| CellLine | `cell-source-taxonomy-id` | `int` | `float` | `TaxonomyId.from-raw()` |

**Root cause:** `activity-transformer.py:70` использует `validate-taxonomy-id-str` (возвращает `str`), в то время как все остальные используют `validate-taxonomy-id` (возвращает `int`) или `TaxonomyId.from-raw()` (возвращает `int`).

**Затронутые файлы:**
- `src/bioetl/domain/schemas/chembl/activity.py:192` — `Series[str]`
- `src/bioetl/domain/contracts/gold/chembl.py:55` — `Series[str]`
- `src/bioetl/application/pipelines/chembl/activity-transformer.py:70` — `validate-taxonomy-id-str`
- `src/bioetl/domain/value-objects/taxonomy-id.py:163` — `validate-taxonomy-id-str()`

---

### N-02: `cell-source-taxonomy-id` — Silver/Gold type mismatch (CRITICAL)

**Проблема:** Silver схема определяет как `int`, Gold как `float` (coerce).

| Слой | Тип | Файл |
|------|-----|------|
| Silver | `Series[int]` | `domain/schemas/chembl/cell-line.py:55` |
| Gold | `Series[float]` (coerce) | `domain/contracts/gold/chembl.py:256` |

**Root cause:** Silver не учитывает nullable int → float coercion convention.

---

### N-03: `action-type-action-type` — redundant prefix (HIGH)

**Проблема:** При flatten nested `action-type` dict с prefix `action-type-`, поле `action-type` внутри даёт `action-type-action-type`.

```python
# activity-transformer.py
-ACTION-TYPE-FIELDS = {
    "action-type": None,      # → action-type-action-type  (REDUNDANT!)
    "description": None,      # → action-type-description  (OK)
    "parent-type": None,      # → action-type-parent-type  (OK)
}
```

**Затронутые файлы:**
- `src/bioetl/application/pipelines/chembl/activity-transformer.py:41`
- `src/bioetl/domain/schemas/chembl/activity.py:162`
- `src/bioetl/domain/contracts/gold/chembl.py:109`
- `configs/pipelines/composite/activity.yaml:237`

---

### N-04: Inconsistent context naming — `pref-name` (HIGH)

**Проблема:** Одно и то же поле (preferred name) именуется по-разному в зависимости от контекста.

| Контекст | Поле в "домашнем" entity | Поле при денормализации в другой entity |
|----------|--------------------------|----------------------------------------|
| Target | `pref-name` | Activity: `target-pref-name` |
| Molecule | `pref-name` | Activity: `molecule-pref-name` |
| Tissue | `pref-name` | Assay Composite: `tissue-pref-name` |

**Это НЕ баг** — для пайплайна Activity контекстные поля *должны* иметь prefix (`target-*`, `molecule-*`), потому что без него неясно какой `pref-name` имеется в виду. Однако следует зафиксировать единую конвенцию.

---

### N-05: Inconsistent context naming — `description` (HIGH)

| Entity | Поле | При денормализации в Activity |
|--------|------|-------------------------------|
| Assay | `description` | `assay-description` |

**Проблема:** В Assay schema поле `description` без prefix, но в Activity при денормализации добавляется `assay-`. Для одного entity (Assay) `assay-type` имеет prefix, а `description` — нет. Это создаёт неконсистентность внутри Assay.

---

### N-06: Cross-provider naming — physicochemical properties (MEDIUM)

Composite Molecule pipeline объединяет ChEMBL и PubChem данные с разными именами для одних и тех же свойств:

| Свойство | ChEMBL (Silver) | PubChem (Silver) | Composite merge |
|----------|-----------------|-------------------|-----------------|
| Lipophilicity | `property-alogp` | `xlogp` | Оба сохранены |
| Polar Surface Area | `property-psa` | `tpsa` | Оба сохранены |
| H-Bond Acceptors | `property-hba` | `hba` | Оба сохранены |
| H-Bond Donors | `property-hbd` | `hbd` | Оба сохранены |
| Rotatable Bonds | `property-rtb` | `rotatable-bond-count` | Каноническое имя: `rotatable-bond-count`; в PubChem поле отсутствует |
| Heavy Atoms | `property-heavy-atoms` | `heavy-atom-count` | Оба сохранены |
| Aromatic Rings | `property-aromatic-rings` | `aromatic-ring-count` | Каноническое имя: `aromatic-ring-count` |
| Molecular Weight | `property-full-mwt` | `molecular-weight` | Оба сохранены |

**Текущий подход:** `preserve-all-sources: true` — сохраняются обе колонки. Это осознанное решение (данные отличаются: ALogP ≠ XLogP3, разные методы расчёта). Но naming convention всё равно нуждается в стандартизации.

---

### N-07: Inconsistent flatten prefix policy (MEDIUM)

| Nested object | Prefix | Примеры |
|--------------|--------|---------|
| `molecule-properties` | `property-` | `property-alogp`, `property-hba` |
| `molecule-hierarchy` | `hierarchy-` | `hierarchy-parent-chembl-id` |
| `molecule-structures` | `""` (пусто) | `canonical-smiles`, `inchi-key` |
| `ligand-efficiency` | `ligand-efficiency-` | `ligand-efficiency-bei` |
| `action-type` | `action-type-` | `action-type-description` |
| `variant-sequence` | `variant-` | `variant-accession` |

**Проблема:** `molecule-structures` раскрывается без prefix, все остальные — с prefix. Причина: `canonical-smiles` шарится между ChEMBL и PubChem и prefix `structure-` был бы длинным. Но это исключение из общего правила.

---

### N-08: Singular/plural ambiguity (LOW)

| Поле | Тип | Назначение |
|------|-----|------------|
| `component-id` | `float` (scalar) | Primary component ID (first from list, для FK join) |
| `component-ids` | `object` (list) | Все component IDs |

Работает корректно, но `component-id` vs `component-ids` не самоочевидно. Лучше: `primary-component-id`.

---

### N-09: InChI Key dual naming (LOW)

| Поле | Источник | Слой |
|------|----------|------|
| `structure-standard-inchi-key` | Top-level alias от ChEMBL API | Silver (Molecule schema, line 41) |
| `inchi-key` | Flattened из `molecule-structures` | Silver + Gold (Molecule schema, line 229) |

Два поля содержат одни и те же данные. `structure-standard-inchi-key` — это top-level alias, `inchi-key` — результат flatten.

---

### N-10: Publication ↔ Activity context naming gap (HIGH)

**Проблема:** Activity денормализует publication-поля с prefix `document-`, но
Publication pipeline использует unified naming из `PublicationBaseSchema`.

| Данные | В Activity | В Publication (unified) | В ChEMBL Document (legacy) |
|--------|-----------|-------------------------|---------------------------|
| Год публикации | `document-year` (int) | `publication-year` (Int64) | `year` → `publication-year` |
| Журнал | `document-journal` (str) | `journal` (str) | `journal` (str) |
| Количество цитирований | — | `citations-received` (Int64) | — |

**Последствия:**
- При будущем composite activity + publication join, поле `document-year` (Activity) и `publication-year` (Publication) содержат одни и те же данные, но именуются по-разному
- Конвенция context prefix `document-*` в Activity конфликтует с unified naming convention `publication-*`

**Root cause:** Activity transformer создавался до Publication unification. Контекстные поля `document-journal` и `document-year` следуют старой конвенции "prefix = source entity name", но Publication pipeline выбрал semantic naming (`publication-year` вместо `document-year`).

**Затронутые файлы:**
- `src/bioetl/application/pipelines/chembl/activity-transformer.py` — field groups `-QUALITY-ANNOTATIONS`
- `src/bioetl/domain/schemas/chembl/activity.py` — `document-year`, `document-journal`
- `src/bioetl/domain/contracts/gold/chembl.py` — Activity Gold schema
- `configs/pipelines/composite/activity.yaml` — column-groups `document-context`

---

## 3. План унификации

### Фаза 1: CRITICAL fixes (type mismatches) — Breaking changes

> **Impact:** Меняет тип данных в Silver/Gold таблицах → требует REBUILD.
>
> **Schema Drift Policy (RULES.md v5.20):** Тип change = **Critical** drift.
> Политика упрощена: только Info (новые поля) и Critical (пропавшее поле / смена типа).
> Уровень Warn (>3 новых полей) удалён.

#### RF-NAMING-01: Унифицировать `target-taxonomy-id` → `float`

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `activity-transformer.py:70` | `validate-taxonomy-id-str` → `validate-taxonomy-id` |
| 2 | `domain/schemas/chembl/activity.py:192` | `Series[str]` → `Series[float]` |
| 3 | `domain/contracts/gold/chembl.py:55` | `Series[str]` → `Series[float]` (coerce=True) |
| 4 | Тесты | Обновить unit tests для ActivityTransformer |
| 5 | Composite configs | `composite/activity.yaml` — обновить `field-validations.target-taxonomy-id.type: integer` |

**Миграция данных:** REBUILD для Activity Silver + Gold.

#### RF-NAMING-02: Унифицировать `cell-source-taxonomy-id` → `float` в Silver

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `domain/schemas/chembl/cell-line.py:55` | `Series[int]` → `Series[float]` |
| 2 | Тесты | Обновить unit tests |

**Миграция данных:** REBUILD для CellLine Silver.

---

### Фаза 2: HIGH fixes (naming) — Breaking changes

> **Impact:** Меняет имена колонок в Silver/Gold → требует REBUILD.

#### RF-NAMING-03: Rename `action-type-action-type` → `action-type`

**Стратегия:** Добавить rename mapping в `-ACTION-TYPE-FIELDS`:

```python
-ACTION-TYPE-FIELDS = {
    "action-type": None,    # flatten → action-type-action-type
    "description": None,    # flatten → action-type-description
    "parent-type": None,    # flatten → action-type-parent-type
}
-ACTION-TYPE-RENAMES = {
    "action-type-action-type": "action-type",  # Remove redundant prefix
}
```

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `activity-transformer.py:40-44` | Добавить `-ACTION-TYPE-RENAMES`, передать в `flatten-nested-dict` |
| 2 | `domain/schemas/chembl/activity.py:162` | `action-type-action-type` → `action-type` |
| 3 | `domain/contracts/gold/chembl.py:109` | `action-type-action-type` → `action-type` |
| 4 | `configs/pipelines/composite/activity.yaml:237` | Обновить column-groups |
| 5 | Тесты | Обновить |

**Риск:** Конфликт имён — `action-type` совпадает с контекстным полем `assay-type`, но это разные данные (action type of molecule-target interaction vs assay type). Нужно проверить, нет ли коллизии в Activity schema.

**Решение:** Нет коллизии — `assay-type` и `action-type` это разные поля. `action-type` = тип действия молекулы на таргет (inhibitor, agonist, etc.).

#### RF-NAMING-04: Зафиксировать конвенцию context-prefix naming

**Правило:** Когда поле из entity A денормализуется в entity B, оно получает prefix `{source-entity}-`:

```
Правильно:
  Target.pref-name        → Activity.target-pref-name
  Target.organism         → Activity.target-organism
  Assay.description       → Activity.assay-description
  Assay.assay-type        → Activity.assay-type  (уже имеет prefix!)
  Tissue.pref-name        → Assay Composite.tissue-pref-name
```

Это ТЕКУЩЕЕ поведение, и оно корректно. Нужно:

| Шаг | Действие |
|-----|----------|
| 1 | Задокументировать правило в RULES.md §2.x "Field Naming Conventions" |
| 2 | Задокументировать правило в ADR (новый ADR-0XX) |

**Не менять:** `Assay.description` (без prefix `assay-`) — это breaking change с малой пользой. Assay `description` — единственное поле без prefix в "домашнем" entity, это legacy. Для новых entity всегда добавлять prefix.

---

### Фаза 3: MEDIUM fixes (convention alignment) — Non-breaking

> **Impact:** Добавляет alias-поля / документацию, не ломает существующие.

#### RF-NAMING-05: Стандартизировать cross-provider naming для Composite Molecule

**Подход:** Переиспользовать паттерн из Publication unification (§0):

1. Создать `MoleculeBaseSchema` в `domain/schemas/common/molecule-base.py` с unified field names
2. Создать `MOLECULE-FIELD-MAPPING` в `domain/mapping/molecule-fields.py` по аналогии с `PUBLICATION-FIELD-MAPPING`
3. Использовать `apply-field-mapping()` в трансформерах

```python
# domain/mapping/molecule-fields.py (по аналогии с publication-fields.py)
-CHEMBL-MOLECULE-MAPPING: Final[dict[str, str]] = {
    "property-alogp": "logp",           # ALogP → unified logp
    "property-psa": "polar-surface-area",
    "property-hba": "hba-count",
    "property-hbd": "hbd-count",
    "property-rtb": "rotatable-bond-count",
    "property-heavy-atoms": "heavy-atom-count",
    "property-aromatic-rings": "aromatic-ring-count",
    "property-full-mwt": "molecular-weight",
}

-PUBCHEM-MOLECULE-MAPPING: Final[dict[str, str]] = {
    "xlogp": "logp",
    "tpsa": "polar-surface-area",
    "hba": "hba-count",
    "hbd": "hbd-count",
    "rotatable-bonds": "rotatable-bond-count",
    "heavy-atom-count": "heavy-atom-count",  # Already canonical
    "aromatic-rings": "aromatic-ring-count",
    "molecular-weight": "molecular-weight",  # Already canonical
}
```

**Важно:** ALogP ≠ XLogP3 — это разные методы расчёта. Unified `logp` в Gold composite
будет содержать coalesced значение с `field-priority: [pubchem, chembl]` и source tracking.
Оригинальные `property-alogp` / `xlogp` сохраняются в Silver каждого провайдера.

| Шаг | Действие |
|-----|----------|
| 1 | Создать `domain/mapping/molecule-fields.py` по шаблону `publication-fields.py` |
| 2 | Создать `domain/schemas/common/molecule-base.py` (unified field names) |
| 3 | Обновить Composite Molecule config с unified naming |
| 4 | Добавить ADR-0XX с обоснованием подхода |

#### RF-NAMING-06: Стандартизировать flatten prefix policy

**Правило:** ВСЕ flattened nested objects используют prefix `{parent-field}-`, кроме `molecule-structures` (legacy exception).

| Шаг | Действие |
|-----|----------|
| 1 | Документировать правило + exception в RULES.md |
| 2 | Добавить комментарий в `molecule-transformer.py:163` объясняющий отсутствие prefix |

#### RF-NAMING-10: Согласовать Activity document context с Publication unified naming

**Проблема:** Activity использует `document-year` / `document-journal`, а Publication ecosystem — `publication-year` / `journal`.

**Стратегия (breaking-now):** Переименовать Activity поля сразу в unified naming (`publication-year`, `journal`, `publication-id`, `publication-doi`/`publication-pmid`/`publication-pmc-id`) без сохранения `document-*`.

| Шаг | Действие |
|-----|----------|
| 1 | В `activity-transformer.py` генерировать publication-* поля и `publication-id`; удалить `document-*` |
| 2 | В Activity Silver/Gold схемах оставить только unified имена |
| 3 | В `composite/activity.yaml` обновить join/field-groups/validations на publication-* |
| 4 | Обновить DQ/data-schema/field-groups на publication-* |
| 5 | Обновить тесты и REBUILD Activity Silver/Gold |

**Обоснование:** Принята стратегия breaking rename без legacy. Unified naming выравнивает Activity с Publication pipelines и убирает дубли контекстных полей.

---

### Фаза 4: LOW fixes (clarity) — Non-breaking

#### RF-NAMING-07: Rename `component-id` → `primary-component-id`

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `target-transformer.py` | `component-id` → `primary-component-id` |
| 2 | Silver/Gold schemas | Rename field |
| 3 | `composite/target.yaml` | Обновить `output-keys`, `join-keys`, `field-priorities` |

**Миграция данных:** REBUILD для Target.

#### RF-NAMING-08: Удалить `structure-standard-inchi-key` alias

Поле `structure-standard-inchi-key` в Molecule Silver schema дублирует `inchi-key`. Одно из них нужно удалить.

| Шаг | Действие |
|-----|----------|
| 1 | Проверить, используется ли `structure-standard-inchi-key` downstream |
| 2 | Если нет — удалить из Silver schema, оставить `inchi-key` |
| 3 | Если да — deprecate с forward alias в Gold |

---

## 4. Deprecation strategy для удаляемого `validate-taxonomy-id-str`

```python
# BEFORE (текущий):
def validate-taxonomy-id-str(value):
    vo = TaxonomyId.from-raw(value)
    return str(vo.value) if vo else None

# AFTER (Phase 1):
# Удалить функцию. Все callers переключить на validate-taxonomy-id.
```

**Единственный caller:** `activity-transformer.py:70` (FieldSpec converter).

---

## 5. Приоритет и зависимости

```
RF-NAMING-01 (taxonomy type) ←── CRITICAL, блокирует downstream joins
RF-NAMING-02 (cell-line type) ←── CRITICAL, может вызвать runtime coercion errors
     │
     ├── RF-NAMING-03 (action-type rename)
     ├── RF-NAMING-04 (document convention)
     ├── RF-NAMING-10 (Activity ↔ Publication naming)
     │
     ├── RF-NAMING-05 (cross-provider molecule) ← зависит от Publication pattern (§0)
     ├── RF-NAMING-06 (flatten prefix doc)
     │
     ├── RF-NAMING-07 (component-id rename)
     └── RF-NAMING-08 (inchi-key dedup)
```

---

## 6. Impact matrix

| Task | Файлов | Тестов | Миграция данных | Composite configs |
|------|--------|--------|-----------------|-------------------|
| RF-NAMING-01 | 5 | ~3-5 | REBUILD Activity | Да |
| RF-NAMING-02 | 1 | ~1-2 | REBUILD CellLine | Нет |
| RF-NAMING-03 | 4+ | ~3-5 | REBUILD Activity | Да |
| RF-NAMING-04 | 0 (doc only) | 0 | Нет | Нет |
| RF-NAMING-05 | 3-5 (new files) | ~3-5 | Нет (additive) | Да |
| RF-NAMING-06 | 0 (doc only) | 0 | Нет | Нет |
| RF-NAMING-07 | 4+ | ~3-5 | REBUILD Target | Да |
| RF-NAMING-08 | 2 | ~1-2 | REBUILD Molecule | Нет |
| RF-NAMING-10 | 1-2 (config) | 0 | Нет (merge-time) | Да |

---

## 7. Рекомендуемый порядок реализации

### Batch 1 (Critical — type safety)
1. **RF-NAMING-01** + **RF-NAMING-02** — одним коммитом, т.к. оба про taxonomy-id type unification

### Batch 2 (High — naming cleanup)
2. **RF-NAMING-03** — action-type rename (isolated change)
3. **RF-NAMING-04** — documentation only
4. **RF-NAMING-10** — Activity ↔ Publication context mapping (config only, non-breaking)

### Batch 3 (Medium — cross-provider unification)
5. **RF-NAMING-05** — Molecule cross-provider naming по паттерну Publication unification
6. **RF-NAMING-06** — flatten prefix documentation

### Batch 4 (Low — polish)
7. **RF-NAMING-07** + **RF-NAMING-08** — component-id + inchi-key cleanup

### Post-migration
8. Один REBUILD для Activity + CellLine + Target + Molecule (можно объединить)

---

## 8. Правила именования (предлагаемые для RULES.md)

### 8.1 Taxonomy ID Convention
- Тип: всегда `float` (nullable int pattern)
- Имя: `{context-prefix}taxonomy-id` (не `tax-id`)
- Converter: `validate-taxonomy-id()` (возвращает `int`, Pandas хранит как `float`)

### 8.2 Context Denormalization Prefix
- При денормализации поля из entity A в entity B: `{source-entity}-{field-name}`
- Пример: `Target.pref-name` → `Activity.target-pref-name`
- Исключение: если поле уже содержит entity prefix (e.g. `assay-type`), дополнительный prefix НЕ добавляется

### 8.3 Nested Object Flatten Prefix
- Default: `{parent-json-field}-{child-key}` (e.g. `ligand-efficiency-bei`)
- Renames разрешены для: удаления redundancy, стандартизации names
- Exception: `molecule-structures` → flatten без prefix (shared naming with PubChem)

### 8.4 Singular vs Plural for List Fields
- Scalar FK: `{entity}-id` (e.g. `component-id`, `protein-classification-id`)
- List field: `{entity}-ids` (e.g. `component-ids`, `protein-classification-ids`)
- Рекомендация: для clarity scalar FK переименовать в `primary-{entity}-id`

---

## Ссылки

### Core Pipeline Files
- **Activity Silver Schema:** `src/bioetl/domain/schemas/chembl/activity.py`
- **Activity Gold Schema:** `src/bioetl/domain/contracts/gold/chembl.py:29-128`
- **Activity Transformer:** `src/bioetl/application/pipelines/chembl/activity-transformer.py`
- **TaxonomyId VO:** `src/bioetl/domain/value-objects/taxonomy-id.py`
- **Composite Configs:** `configs/pipelines/composite/{entity}.yaml`
- **Validation Matrix:** `docs/03-data-model/pipeline-validation-matrix.md`

### Publication Unification Precedent (main)
- **Publication Base Schema:** `src/bioetl/domain/schemas/common/publication-base.py`
- **Publication Field Mapping:** `src/bioetl/domain/mapping/publication-fields.py`
- **ADR-030 (archived):** `docs/99-archive/decisions/ADR-030-publication-field-unification.md`
- **Composite Publication Config:** `configs/pipelines/composite/publication.yaml`
- **S2 Publication Schema:** `src/bioetl/domain/schemas/semanticscholar/publication.py`
- **ChEMBL Publication Transformer:** `src/bioetl/application/pipelines/chembl/publication-transformer.py`

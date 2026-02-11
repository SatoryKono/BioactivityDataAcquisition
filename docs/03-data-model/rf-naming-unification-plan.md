# RF-NAMING: План унификации наименований полей

*Версия: 2.0.0 | Дата: 2026-02-11 | Обновлено с учётом main (7e265aa)*

---

## 0. Контекст: Publication Unification Precedent

На main уже существует полноценная **экосистема Publication-пайплайнов** (5 провайдеров:
ChEMBL, CrossRef, OpenAlex, PubMed, Semantic Scholar), в которой cross-provider
field naming **уже решён** через:

1. **`PublicationBaseSchema`** (`domain/schemas/common/publication_base.py`) —
   общая base-схема с unified field names
2. **`PUBLICATION_FIELD_MAPPING`** (`domain/mapping/publication_fields.py`) —
   bidirectional маппинг provider → unified names
3. **`apply_field_mapping()`** — runtime rename при трансформации
4. **ADR-030** (archived) — Publication Field Naming Unification decision record

Ключевые унифицированные имена publication:

| Provider name | Unified name | Провайдеры |
|---------------|--------------|------------|
| `year` | `publication_year` | All 5 |
| `citation_count` | `citations_received` | CrossRef, OpenAlex, S2 |
| `reference_count` | `citations_made` | CrossRef, OpenAlex, S2 |
| `first_page` / `last_page` | `page_first` / `page_last` | CrossRef, OpenAlex, PubMed |
| `doc_type` / `source_type` | `publication_type` | ChEMBL, CrossRef, OpenAlex |
| `is_open_access` | `is_oa` | All |
| `affiliations` | `affiliation_list` | OpenAlex, PubMed |

**Вывод для core pipelines:** Паттерн `BaseSchema` + `FIELD_MAPPING` dict + `apply_field_mapping()`
является проверенным подходом и должен быть переиспользован для унификации
Molecule cross-provider naming (N-06).

---

## 1. Обнаруженные проблемы

### 1.1 Инвентаризация несоответствий

Всего выявлено **10 категорий** несоответствий, затрагивающих **~30 полей** в 4 основных,
6 вспомогательных и 5 publication-пайплайнах.

| # | Severity | Категория | Пример |
|---|----------|-----------|--------|
| N-01 | CRITICAL | Type mismatch: `taxonomy_id` | Activity: `str`, все остальные: `float` |
| N-02 | CRITICAL | Type mismatch: `cell_source_taxonomy_id` | Silver: `int`, Gold: `float` |
| N-03 | HIGH | Redundant prefix: `action_type_action_type` | Двойной префикс при flatten |
| N-04 | HIGH | Inconsistent context naming: `pref_name` | Target: `pref_name`, Activity: `target_pref_name`, Assay Composite: `tissue_pref_name` |
| N-05 | HIGH | Inconsistent context naming: `description` | Assay: `description`, Activity: `assay_description` |
| N-06 | MEDIUM | Cross-provider naming: physicochemical properties | ChEMBL: `property_alogp`, PubChem: `xlogp` |
| N-07 | MEDIUM | Inconsistent flatten prefixes | `property_*`, `hierarchy_*`, `ligand_efficiency_*`, но `canonical_smiles` без prefix |
| N-08 | LOW | Singular/plural ambiguity | `component_id` (scalar) vs `component_ids` (list) |
| N-09 | LOW | InChI Key dual naming | `structure_standard_inchi_key` (top-level alias) vs `inchikey` (flattened) |
| N-10 | HIGH | Publication ↔ Activity context naming gap | Activity: `document_year`, Publication unified: `publication_year`; Activity: `document_journal`, Publication: `journal` |

---

## 2. Детальный анализ каждой проблемы

### N-01: `taxonomy_id` — type mismatch (CRITICAL)

**Проблема:** Одни и те же данные (NCBI Taxonomy ID) имеют разные типы.

| Пайплайн | Поле | Silver тип | Gold тип | Converter |
|----------|------|------------|----------|-----------|
| Activity | `target_taxonomy_id` | `str` | `str` | `validate_taxonomy_id_str` |
| Assay | `assay_taxonomy_id` | `float` | `float` | `validate_taxonomy_id` |
| Assay | `variant_taxonomy_id` | `float` | `float` | `validate_taxonomy_id` |
| Target | `taxonomy_id` | `float` | `float` | `TaxonomyId.from_raw()` |
| CellLine | `cell_source_taxonomy_id` | `int` | `float` | `TaxonomyId.from_raw()` |

**Root cause:** `activity_transformer.py:70` использует `validate_taxonomy_id_str` (возвращает `str`), в то время как все остальные используют `validate_taxonomy_id` (возвращает `int`) или `TaxonomyId.from_raw()` (возвращает `int`).

**Затронутые файлы:**
- `src/bioetl/domain/schemas/chembl/activity.py:192` — `Series[str]`
- `src/bioetl/domain/contracts/gold/chembl.py:55` — `Series[str]`
- `src/bioetl/application/pipelines/chembl/activity_transformer.py:70` — `validate_taxonomy_id_str`
- `src/bioetl/domain/value_objects/taxonomy_id.py:163` — `validate_taxonomy_id_str()`

---

### N-02: `cell_source_taxonomy_id` — Silver/Gold type mismatch (CRITICAL)

**Проблема:** Silver схема определяет как `int`, Gold как `float` (coerce).

| Слой | Тип | Файл |
|------|-----|------|
| Silver | `Series[int]` | `domain/schemas/chembl/cell_line.py:55` |
| Gold | `Series[float]` (coerce) | `domain/contracts/gold/chembl.py:256` |

**Root cause:** Silver не учитывает nullable int → float coercion convention.

---

### N-03: `action_type_action_type` — redundant prefix (HIGH)

**Проблема:** При flatten nested `action_type` dict с prefix `action_type_`, поле `action_type` внутри даёт `action_type_action_type`.

```python
# activity_transformer.py
_ACTION_TYPE_FIELDS = {
    "action_type": None,      # → action_type_action_type  (REDUNDANT!)
    "description": None,      # → action_type_description  (OK)
    "parent_type": None,      # → action_type_parent_type  (OK)
}
```

**Затронутые файлы:**
- `src/bioetl/application/pipelines/chembl/activity_transformer.py:41`
- `src/bioetl/domain/schemas/chembl/activity.py:162`
- `src/bioetl/domain/contracts/gold/chembl.py:109`
- `configs/pipelines/composite/activity.yaml:237`

---

### N-04: Inconsistent context naming — `pref_name` (HIGH)

**Проблема:** Одно и то же поле (preferred name) именуется по-разному в зависимости от контекста.

| Контекст | Поле в "домашнем" entity | Поле при денормализации в другой entity |
|----------|--------------------------|----------------------------------------|
| Target | `pref_name` | Activity: `target_pref_name` |
| Molecule | `pref_name` | Activity: `molecule_pref_name` |
| Tissue | `pref_name` | Assay Composite: `tissue_pref_name` |

**Это НЕ баг** — для пайплайна Activity контекстные поля *должны* иметь prefix (`target_*`, `molecule_*`), потому что без него неясно какой `pref_name` имеется в виду. Однако следует зафиксировать единую конвенцию.

---

### N-05: Inconsistent context naming — `description` (HIGH)

| Entity | Поле | При денормализации в Activity |
|--------|------|-------------------------------|
| Assay | `description` | `assay_description` |

**Проблема:** В Assay schema поле `description` без prefix, но в Activity при денормализации добавляется `assay_`. Для одного entity (Assay) `assay_type` имеет prefix, а `description` — нет. Это создаёт неконсистентность внутри Assay.

---

### N-06: Cross-provider naming — physicochemical properties (MEDIUM)

Composite Molecule pipeline объединяет ChEMBL и PubChem данные с разными именами для одних и тех же свойств:

| Свойство | ChEMBL (Silver) | PubChem (Silver) | Composite merge |
|----------|-----------------|-------------------|-----------------|
| Lipophilicity | `property_alogp` | `xlogp` | Оба сохранены |
| Polar Surface Area | `property_psa` | `tpsa` | Оба сохранены |
| H-Bond Acceptors | `property_hba` | `hba` | Оба сохранены |
| H-Bond Donors | `property_hbd` | `hbd` | Оба сохранены |
| Rotatable Bonds | `property_rtb` | `rotatable_bonds` | Оба сохранены |
| Heavy Atoms | `property_heavy_atoms` | `heavy_atom_count` | Оба сохранены |
| Aromatic Rings | `property_aromatic_rings` | `aromatic_rings` | Оба сохранены |
| Molecular Weight | `property_full_mwt` | `molecular_weight` | Оба сохранены |

**Текущий подход:** `preserve_all_sources: true` — сохраняются обе колонки. Это осознанное решение (данные отличаются: ALogP ≠ XLogP3, разные методы расчёта). Но naming convention всё равно нуждается в стандартизации.

---

### N-07: Inconsistent flatten prefix policy (MEDIUM)

| Nested object | Prefix | Примеры |
|--------------|--------|---------|
| `molecule_properties` | `property_` | `property_alogp`, `property_hba` |
| `molecule_hierarchy` | `hierarchy_` | `hierarchy_parent_chembl_id` |
| `molecule_structures` | `""` (пусто) | `canonical_smiles`, `inchikey` |
| `ligand_efficiency` | `ligand_efficiency_` | `ligand_efficiency_bei` |
| `action_type` | `action_type_` | `action_type_description` |
| `variant_sequence` | `variant_` | `variant_accession` |

**Проблема:** `molecule_structures` раскрывается без prefix, все остальные — с prefix. Причина: `canonical_smiles` шарится между ChEMBL и PubChem и prefix `structure_` был бы длинным. Но это исключение из общего правила.

---

### N-08: Singular/plural ambiguity (LOW)

| Поле | Тип | Назначение |
|------|-----|------------|
| `component_id` | `float` (scalar) | Primary component ID (first from list, для FK join) |
| `component_ids` | `object` (list) | Все component IDs |

Работает корректно, но `component_id` vs `component_ids` не самоочевидно. Лучше: `primary_component_id`.

---

### N-09: InChI Key dual naming (LOW)

| Поле | Источник | Слой |
|------|----------|------|
| `structure_standard_inchi_key` | Top-level alias от ChEMBL API | Silver (Molecule schema, line 41) |
| `inchikey` | Flattened из `molecule_structures` | Silver + Gold (Molecule schema, line 229) |

Два поля содержат одни и те же данные. `structure_standard_inchi_key` — это top-level alias, `inchikey` — результат flatten.

---

### N-10: Publication ↔ Activity context naming gap (HIGH)

**Проблема:** Activity денормализует publication-поля с prefix `document_`, но
Publication pipeline использует unified naming из `PublicationBaseSchema`.

| Данные | В Activity | В Publication (unified) | В ChEMBL Document (legacy) |
|--------|-----------|-------------------------|---------------------------|
| Год публикации | `document_year` (int) | `publication_year` (Int64) | `year` → `publication_year` |
| Журнал | `document_journal` (str) | `journal` (str) | `journal` (str) |
| Количество цитирований | — | `citations_received` (Int64) | — |

**Последствия:**
- При будущем composite activity + publication join, поле `document_year` (Activity) и `publication_year` (Publication) содержат одни и те же данные, но именуются по-разному
- Конвенция context prefix `document_*` в Activity конфликтует с unified naming convention `publication_*`

**Root cause:** Activity transformer создавался до Publication unification. Контекстные поля `document_journal` и `document_year` следуют старой конвенции "prefix = source entity name", но Publication pipeline выбрал semantic naming (`publication_year` вместо `document_year`).

**Затронутые файлы:**
- `src/bioetl/application/pipelines/chembl/activity_transformer.py` — field groups `_QUALITY_ANNOTATIONS`
- `src/bioetl/domain/schemas/chembl/activity.py` — `document_year`, `document_journal`
- `src/bioetl/domain/contracts/gold/chembl.py` — Activity Gold schema
- `configs/pipelines/composite/activity.yaml` — column_groups `document_context`

---

## 3. План унификации

### Фаза 1: CRITICAL fixes (type mismatches) — Breaking changes

> **Impact:** Меняет тип данных в Silver/Gold таблицах → требует REBUILD.

#### RF-NAMING-01: Унифицировать `target_taxonomy_id` → `float`

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `activity_transformer.py:70` | `validate_taxonomy_id_str` → `validate_taxonomy_id` |
| 2 | `domain/schemas/chembl/activity.py:192` | `Series[str]` → `Series[float]` |
| 3 | `domain/contracts/gold/chembl.py:55` | `Series[str]` → `Series[float]` (coerce=True) |
| 4 | Тесты | Обновить unit tests для ActivityTransformer |
| 5 | Composite configs | `composite/activity.yaml` — обновить `field_validations.target_taxonomy_id.type: integer` |

**Миграция данных:** REBUILD для Activity Silver + Gold.

#### RF-NAMING-02: Унифицировать `cell_source_taxonomy_id` → `float` в Silver

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `domain/schemas/chembl/cell_line.py:55` | `Series[int]` → `Series[float]` |
| 2 | Тесты | Обновить unit tests |

**Миграция данных:** REBUILD для CellLine Silver.

---

### Фаза 2: HIGH fixes (naming) — Breaking changes

> **Impact:** Меняет имена колонок в Silver/Gold → требует REBUILD.

#### RF-NAMING-03: Rename `action_type_action_type` → `action_type`

**Стратегия:** Добавить rename mapping в `_ACTION_TYPE_FIELDS`:

```python
_ACTION_TYPE_FIELDS = {
    "action_type": None,    # flatten → action_type_action_type
    "description": None,    # flatten → action_type_description
    "parent_type": None,    # flatten → action_type_parent_type
}
_ACTION_TYPE_RENAMES = {
    "action_type_action_type": "action_type",  # Remove redundant prefix
}
```

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `activity_transformer.py:40-44` | Добавить `_ACTION_TYPE_RENAMES`, передать в `flatten_nested_dict` |
| 2 | `domain/schemas/chembl/activity.py:162` | `action_type_action_type` → `action_type` |
| 3 | `domain/contracts/gold/chembl.py:109` | `action_type_action_type` → `action_type` |
| 4 | `configs/pipelines/composite/activity.yaml:237` | Обновить column_groups |
| 5 | Тесты | Обновить |

**Риск:** Конфликт имён — `action_type` совпадает с контекстным полем `assay_type`, но это разные данные (action type of molecule-target interaction vs assay type). Нужно проверить, нет ли коллизии в Activity schema.

**Решение:** Нет коллизии — `assay_type` и `action_type` это разные поля. `action_type` = тип действия молекулы на таргет (inhibitor, agonist, etc.).

#### RF-NAMING-04: Зафиксировать конвенцию context-prefix naming

**Правило:** Когда поле из entity A денормализуется в entity B, оно получает prefix `{source_entity}_`:

```
Правильно:
  Target.pref_name        → Activity.target_pref_name
  Target.organism         → Activity.target_organism
  Assay.description       → Activity.assay_description
  Assay.assay_type        → Activity.assay_type  (уже имеет prefix!)
  Tissue.pref_name        → Assay Composite.tissue_pref_name
```

Это ТЕКУЩЕЕ поведение, и оно корректно. Нужно:

| Шаг | Действие |
|-----|----------|
| 1 | Задокументировать правило в RULES.md §2.x "Field Naming Conventions" |
| 2 | Задокументировать правило в ADR (новый ADR-0XX) |

**Не менять:** `Assay.description` (без prefix `assay_`) — это breaking change с малой пользой. Assay `description` — единственное поле без prefix в "домашнем" entity, это legacy. Для новых entity всегда добавлять prefix.

---

### Фаза 3: MEDIUM fixes (convention alignment) — Non-breaking

> **Impact:** Добавляет alias-поля / документацию, не ломает существующие.

#### RF-NAMING-05: Стандартизировать cross-provider naming для Composite Molecule

**Подход:** Переиспользовать паттерн из Publication unification (§0):

1. Создать `MoleculeBaseSchema` в `domain/schemas/common/molecule_base.py` с unified field names
2. Создать `MOLECULE_FIELD_MAPPING` в `domain/mapping/molecule_fields.py` по аналогии с `PUBLICATION_FIELD_MAPPING`
3. Использовать `apply_field_mapping()` в трансформерах

```python
# domain/mapping/molecule_fields.py (по аналогии с publication_fields.py)
_CHEMBL_MOLECULE_MAPPING: Final[dict[str, str]] = {
    "property_alogp": "logp",           # ALogP → unified logp
    "property_psa": "polar_surface_area",
    "property_hba": "hba_count",
    "property_hbd": "hbd_count",
    "property_rtb": "rotatable_bond_count",
    "property_heavy_atoms": "heavy_atom_count",
    "property_aromatic_rings": "aromatic_ring_count",
    "property_full_mwt": "molecular_weight",
}

_PUBCHEM_MOLECULE_MAPPING: Final[dict[str, str]] = {
    "xlogp": "logp",
    "tpsa": "polar_surface_area",
    "hba": "hba_count",
    "hbd": "hbd_count",
    "rotatable_bonds": "rotatable_bond_count",
    "heavy_atom_count": "heavy_atom_count",  # Already canonical
    "aromatic_rings": "aromatic_ring_count",
    "molecular_weight": "molecular_weight",  # Already canonical
}
```

**Важно:** ALogP ≠ XLogP3 — это разные методы расчёта. Unified `logp` в Gold composite
будет содержать coalesced значение с `field_priority: [pubchem, chembl]` и source tracking.
Оригинальные `property_alogp` / `xlogp` сохраняются в Silver каждого провайдера.

| Шаг | Действие |
|-----|----------|
| 1 | Создать `domain/mapping/molecule_fields.py` по шаблону `publication_fields.py` |
| 2 | Создать `domain/schemas/common/molecule_base.py` (unified field names) |
| 3 | Обновить Composite Molecule config с unified naming |
| 4 | Добавить ADR-0XX с обоснованием подхода |

#### RF-NAMING-06: Стандартизировать flatten prefix policy

**Правило:** ВСЕ flattened nested objects используют prefix `{parent_field}_`, кроме `molecule_structures` (legacy exception).

| Шаг | Действие |
|-----|----------|
| 1 | Документировать правило + exception в RULES.md |
| 2 | Добавить комментарий в `molecule_transformer.py:163` объясняющий отсутствие prefix |

#### RF-NAMING-10: Согласовать Activity document context с Publication unified naming

**Проблема:** Activity использует `document_year` / `document_journal`, а Publication ecosystem — `publication_year` / `journal`.

**Стратегия:** НЕ переименовывать Activity поля (breaking change с малой пользой). Вместо этого:

| Шаг | Действие |
|-----|----------|
| 1 | В будущем Composite Activity + Publication merge, добавить field_mapping: `document_year` → `publication_year` |
| 2 | Документировать маппинг в `configs/pipelines/composite/activity.yaml` merge section |
| 3 | В Gold Composite Activity schema использовать unified name `publication_year` |

**Обоснование:** Activity Silver хранит денормализованные контекстные поля (prefix `document_*`). Publication Silver использует unified naming. Reconciliation происходит в Composite merge layer, не в отдельных Silver-схемах. Это согласуется с паттерном Publication unification, где rename тоже выполняется через `FIELD_MAPPING`, а не через переименование в исходном Silver.

---

### Фаза 4: LOW fixes (clarity) — Non-breaking

#### RF-NAMING-07: Rename `component_id` → `primary_component_id`

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | `target_transformer.py` | `component_id` → `primary_component_id` |
| 2 | Silver/Gold schemas | Rename field |
| 3 | `composite/target.yaml` | Обновить `output_keys`, `join_keys`, `field_priorities` |

**Миграция данных:** REBUILD для Target.

#### RF-NAMING-08: Удалить `structure_standard_inchi_key` alias

Поле `structure_standard_inchi_key` в Molecule Silver schema дублирует `inchikey`. Одно из них нужно удалить.

| Шаг | Действие |
|-----|----------|
| 1 | Проверить, используется ли `structure_standard_inchi_key` downstream |
| 2 | Если нет — удалить из Silver schema, оставить `inchikey` |
| 3 | Если да — deprecate с forward alias в Gold |

---

## 4. Deprecation strategy для удаляемого `validate_taxonomy_id_str`

```python
# BEFORE (текущий):
def validate_taxonomy_id_str(value):
    vo = TaxonomyId.from_raw(value)
    return str(vo.value) if vo else None

# AFTER (Phase 1):
# Удалить функцию. Все callers переключить на validate_taxonomy_id.
```

**Единственный caller:** `activity_transformer.py:70` (FieldSpec converter).

---

## 5. Приоритет и зависимости

```
RF-NAMING-01 (taxonomy type) ←── CRITICAL, блокирует downstream joins
RF-NAMING-02 (cell_line type) ←── CRITICAL, может вызвать runtime coercion errors
     │
     ├── RF-NAMING-03 (action_type rename)
     ├── RF-NAMING-04 (document convention)
     ├── RF-NAMING-10 (Activity ↔ Publication naming)
     │
     ├── RF-NAMING-05 (cross-provider molecule) ← зависит от Publication pattern (§0)
     ├── RF-NAMING-06 (flatten prefix doc)
     │
     ├── RF-NAMING-07 (component_id rename)
     └── RF-NAMING-08 (inchikey dedup)
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
1. **RF-NAMING-01** + **RF-NAMING-02** — одним коммитом, т.к. оба про taxonomy_id type unification

### Batch 2 (High — naming cleanup)
2. **RF-NAMING-03** — action_type rename (isolated change)
3. **RF-NAMING-04** — documentation only
4. **RF-NAMING-10** — Activity ↔ Publication context mapping (config only, non-breaking)

### Batch 3 (Medium — cross-provider unification)
5. **RF-NAMING-05** — Molecule cross-provider naming по паттерну Publication unification
6. **RF-NAMING-06** — flatten prefix documentation

### Batch 4 (Low — polish)
7. **RF-NAMING-07** + **RF-NAMING-08** — component_id + inchikey cleanup

### Post-migration
8. Один REBUILD для Activity + CellLine + Target + Molecule (можно объединить)

---

## 8. Правила именования (предлагаемые для RULES.md)

### 8.1 Taxonomy ID Convention
- Тип: всегда `float` (nullable int pattern)
- Имя: `{context_prefix}taxonomy_id` (не `tax_id`)
- Converter: `validate_taxonomy_id()` (возвращает `int`, Pandas хранит как `float`)

### 8.2 Context Denormalization Prefix
- При денормализации поля из entity A в entity B: `{source_entity}_{field_name}`
- Пример: `Target.pref_name` → `Activity.target_pref_name`
- Исключение: если поле уже содержит entity prefix (e.g. `assay_type`), дополнительный prefix НЕ добавляется

### 8.3 Nested Object Flatten Prefix
- Default: `{parent_json_field}_{child_key}` (e.g. `ligand_efficiency_bei`)
- Renames разрешены для: удаления redundancy, стандартизации names
- Exception: `molecule_structures` → flatten без prefix (shared naming with PubChem)

### 8.4 Singular vs Plural for List Fields
- Scalar FK: `{entity}_id` (e.g. `component_id`, `protein_classification_id`)
- List field: `{entity}_ids` (e.g. `component_ids`, `protein_classification_ids`)
- Рекомендация: для clarity scalar FK переименовать в `primary_{entity}_id`

---

## Ссылки

### Core Pipeline Files
- **Activity Silver Schema:** `src/bioetl/domain/schemas/chembl/activity.py`
- **Activity Gold Schema:** `src/bioetl/domain/contracts/gold/chembl.py:29-128`
- **Activity Transformer:** `src/bioetl/application/pipelines/chembl/activity_transformer.py`
- **TaxonomyId VO:** `src/bioetl/domain/value_objects/taxonomy_id.py`
- **Composite Configs:** `configs/pipelines/composite/{entity}.yaml`
- **Validation Matrix:** `docs/03-data-model/pipeline-validation-matrix.md`

### Publication Unification Precedent (main)
- **Publication Base Schema:** `src/bioetl/domain/schemas/common/publication_base.py`
- **Publication Field Mapping:** `src/bioetl/domain/mapping/publication_fields.py`
- **ADR-030 (archived):** `docs/99-archive/decisions/ADR-030-publication-field-unification.md`
- **Composite Publication Config:** `configs/pipelines/composite/publication.yaml`
- **S2 Publication Schema:** `src/bioetl/domain/schemas/semanticscholar/publication.py`
- **ChEMBL Publication Transformer:** `src/bioetl/application/pipelines/chembl/publication_transformer.py`

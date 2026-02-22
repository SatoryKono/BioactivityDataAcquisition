# Prompt: Оптимизация конфигурационных файлов BioETL — устранение дублирования

**Цель:** Снизить дублирование параметров в YAML-конфигурациях проекта. Каждый параметр
MUST быть определён ровно в одном месте (Single Source of Truth). Допускается
переопределение не более 1–3 параметров в дочернем конфиге. Каждое переопределение
MUST содержать комментарий-обоснование (`# Override: <причина>`).

---

## 1. Контекст и текущее состояние

### 1.1 Структура конфигов

```
configs/
├── pipelines/
│   ├── _base.yaml              ← шаблон по умолчанию
│   └── {provider}/{entity}.yaml ← 27 pipeline-конфигов
├── quality/
│   ├── _defaults.yaml           ← глобальные DQ-пороги
│   ├── providers/{provider}.yaml
│   └── entities/{provider}/{entity}.yaml
├── filters/
│   ├── _defaults.yaml
│   ├── providers/{provider}.yaml
│   └── entities/{provider}/{entity}.yaml
└── sources/
    └── {provider}.yaml          ← настройки API-источников
```

### 1.2 Действующие ADR

- **ADR-027**: Hierarchical DQ Config (4-level merge)
- **ADR-028**: Filter Rules Externalization
- **ADR-029**: Convention-based Path Resolution

### 1.3 Действующий merge-порядок

```
_defaults.yaml → providers/{provider}.yaml → entities/{provider}/{entity}.yaml → inline overrides
```

---

## 2. Выявленные паттерны дублирования

### 2.1 CRITICAL — DQ-пороги дублируются в двух SSOT

**Проблема:** `soft_fail_threshold` и `hard_fail_threshold` определены одновременно в
`pipelines/_base.yaml` (строки 10–11) И в `quality/_defaults.yaml` (строки 17–18) с
идентичными значениями (0.05 / 0.20).

```yaml
# configs/pipelines/_base.yaml (строки 9-16)
dq_overrides:
  soft_fail_threshold: 0.05    # ← ДУБЛЬ
  hard_fail_threshold: 0.20    # ← ДУБЛЬ
  strict_validation: false     # ← ДУБЛЬ (то же в quality/_defaults.yaml:23)
  invalid_record_policy: "quarantine"  # ← ДУБЛЬ (то же в quality/_defaults.yaml:28)
  report:
    enabled: true              # ← ДУБЛЬ (то же в quality/_defaults.yaml:34)
    format: "json"             # ← ДУБЛЬ
    include_sample_failures: true
    sample_size: 10

# configs/quality/_defaults.yaml (строки 16-38)
thresholds:
  soft_fail: 0.05             # ← SSOT (должен быть единственным)
  hard_fail: 0.20
strict_validation: false
invalid_record_policy: quarantine
report:
  enabled: true
  format: json
  ...
```

**Риск:** При изменении порога в одном файле второй рассинхронизируется.

**Решение:** Удалить блок `dq_overrides` целиком из `_base.yaml`. DQ-параметры уже
загружаются через `DQConfigLoader` из `quality/_defaults.yaml`. Оставить только пустой
маркер:

```yaml
# configs/pipelines/_base.yaml
# DQ configuration: loaded from configs/quality/ hierarchy (ADR-027).
# Override only in entity pipeline config if needed (max 1-3 params with # Override: comment).
dq_overrides: {}
```

---

### 2.2 HIGH — SCD2-блок копипастится в 20+ файлах

**Проблема:** Идентичный блок sink.gold.scd_config повторяется дословно в 20 из 27
pipeline-конфигов:

```yaml
# Дублируется в: chembl/target, chembl/molecule, chembl/cell_line,
# chembl/compound_record, chembl/tissue, chembl/assay, pubmed/publication,
# openalex/publication, crossref/publication, semanticscholar/publication,
# uniprot/protein, uniprot/idmapping, pubchem/compound, и т.д.
gold:
  mode: scd2
  scd_config:
    valid_from: _valid_from
    valid_to: _valid_to
    is_current: _is_current
    version: _version
```

**Решение:** Вынести SCD2 как дефолт в `_base.yaml`:

```yaml
# configs/pipelines/_base.yaml
sink:
  gold:
    enabled: true
    format: delta
    mode: scd2                  # Default: SCD Type 2 for all entities
    scd_config:                 # Default SCD2 column names
      valid_from: _valid_from
      valid_to: _valid_to
      is_current: _is_current
      version: _version
    deterministic: true
    ...
```

В дочерних pipeline-конфигах SCD2-блок полностью удаляется. Исключения
(publication_similarity, publication_term — `mode: overwrite`) сохраняют ТОЛЬКО
переопределённый параметр с комментарием:

```yaml
# configs/pipelines/chembl/publication_similarity.yaml
sink:
  gold:
    # Override: similarity scores are computed fresh each run, no SCD tracking needed
    mode: overwrite
```

---

### 2.3 HIGH — flat_structure: true дублируется в publication-пайплайнах

**Проблема:** `flat_structure: true` задаётся для bronze/silver/gold в 5 publication
pipeline-конфигах (pubmed, openalex, crossref, semanticscholar, chembl/publication)
с идентичным комментарием.

```yaml
# Повторяется 5 раз:
sink:
  bronze:
    flat_structure: true  # Path already includes provider/entity
  silver:
    flat_structure: true
  gold:
    flat_structure: true
```

**Решение (вариант A — рекомендуемый):** `flat_structure: true` уже задан в `_base.yaml`
(строки 34, 48, 63). Удалить дублирующие переопределения из дочерних конфигов, так как
они идентичны дефолту.

**Решение (вариант B — если нужна категоризация):** Ввести provider-level pipeline
defaults `configs/pipelines/{provider}/_provider.yaml`, которые наследуются всеми
entity-конфигами этого провайдера. Тогда `flat_structure` задаётся один раз для
провайдера.

---

### 2.4 MEDIUM — technical_primary_key и silver/gold_table формульные

**Проблема:** Каждый pipeline-конфиг повторяет:

```yaml
technical_primary_key: "entity_id"  # Одинаков в 27 из 27 файлов
silver_table: "{provider}_{entity}" # Всегда формула от provider+entity
gold_table: "{provider}_{entity}"   # Всегда формула от provider+entity
```

**Решение:** Вынести `technical_primary_key: "entity_id"` в `_base.yaml` как дефолт.
Вычислять `silver_table` / `gold_table` автоматически из `provider` + `entity_type` в
`PipelineConfigLoader`, если не заданы явно. Удалить из всех 27 entity-конфигов.

**Изменение в коде (PipelineConfigLoader):**

```python
# В load_pipeline_config() или при сборке PipelineConfig:
if not raw_config.get("silver_table"):
    raw_config["silver_table"] = f"{provider}_{entity_type}"
if not raw_config.get("gold_table"):
    raw_config["gold_table"] = f"{provider}_{entity_type}"
if not raw_config.get("technical_primary_key"):
    raw_config["technical_primary_key"] = "entity_id"
```

---

### 2.5 MEDIUM — Бойлерплейт-комментарии копируются дословно

**Проблема:** Блоки комментариев про DQ/Filter hierarchy копируются в 20+ файлов:

```yaml
# Один и тот же текст в каждом pipeline-конфиге:
# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/quality/_defaults.yaml (global defaults)
#   2. configs/quality/providers/{provider}.yaml (provider-specific)
#   3. configs/quality/entities/{provider}/{entity}.yaml (entity-specific)

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filters/_defaults.yaml (global defaults)
#   2. configs/filters/providers/{provider}.yaml (provider-specific)
#   3. configs/filters/entities/{provider}/{entity}.yaml (entity-specific)
```

**Решение:** Удалить из entity-конфигов. Задокументировать один раз в `_base.yaml`
(уже есть) и в CONFIG-GUIDE.md. В entity-конфигах оставить однострочную ссылку:

```yaml
# DQ & Filters: loaded via hierarchy (ADR-027/028/029). See _base.yaml for details.
```

---

### 2.6 MEDIUM — circuit_breaker дублируется в _base.yaml и sources

**Проблема:** `circuit_breaker` с идентичными значениями (`failure_threshold: 5`,
`recovery_timeout: 300`) определён в `pipelines/_base.yaml` И во всех
`sources/{provider}.yaml`.

**Решение:** Оставить `circuit_breaker` только в `sources/{provider}.yaml` — это
настройки устойчивости конкретного API-источника. Удалить из `_base.yaml`.

---

### 2.7 LOW — version: "1.2.0" повторяется

**Проблема:** `version: "1.2.0"` задана в 20+ pipeline-конфигах.

**Решение:** Вынести в `_base.yaml` как дефолт. Переопределять только при реальном
отличии версии конфига (publication_similarity v2.1.0 и т.д.):

```yaml
# configs/pipelines/chembl/publication_similarity.yaml
# Override: v2.1.0 schema redesign after ADR-024 naming migration
version: "2.1.0"
```

---

### 2.8 LOW — loading_strategy: full_scan_only с одинаковым комментарием

**Проблема:** `loading_strategy: full_scan_only` с комментарием про "API offset
instability" повторяется в 6 файлах (все publication + subcellular_fraction +
publication_similarity + publication_term).

**Решение:** Не является дублированием в строгом смысле (разные entity действительно
нуждаются в full_scan), но комментарий можно сократить до:

```yaml
# Override: full_scan required — API doesn't support stable incremental cursors
loading_strategy: full_scan_only
```

---

## 3. Правило переопределения (Override Policy)

### 3.1 Что разрешено переопределять в entity pipeline config

Максимум **1–3 параметра** из следующего списка:

| # | Параметр | Когда переопределять |
|---|----------|---------------------|
| 1 | `sink.gold.mode` | Если entity не использует SCD2 (напр. `overwrite`) |
| 2 | `sink.silver.partition_by` | Entity-specific партиционирование |
| 3 | `batch_size` | Если объём данных entity сильно отличается от дефолта |
| 4 | `loading_strategy` | Если entity требует `full_scan_only` |
| 5 | `page_size_override` | Если API endpoint имеет другой лимит |
| 6 | `version` | Если версия конфига отличается от дефолта |

Любой другой параметр **MUST** быть в `_base.yaml`, `quality/`, `filters/`, или `sources/`.

### 3.2 Формат комментария переопределения

Каждый переопределённый параметр **MUST** иметь комментарий в формате:

```yaml
# Override: <краткое обоснование почему значение отличается от дефолта>
parameter: value
```

Примеры:

```yaml
# Override: reference table with ~1.5K records, smaller batches for full load
batch_size: 500

# Override: similarity scores recomputed each run, no history tracking needed
mode: overwrite

# Override: smaller page size for publication endpoint (full_scan_only strategy)
page_size_override: 16

# Override: partition by molecule_type for query performance
partition_by: ["molecule_type"]
```

---

## 4. Целевое состояние pipeline-конфигов (After)

### 4.1 Минимальный конфиг (нет переопределений)

```yaml
# configs/pipelines/chembl/cell_line.yaml
# ChEMBL Cell Line — inherits all defaults from _base.yaml.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline_name: chembl_cell_line
provider: chembl
entity_type: cell_line
schema_file: ../../schemas/chembl/cell_line.yaml
description: "Extract cell lines from ChEMBL API"

business_primary_keys: ["cell_id"]
```

**Всё остальное** (`technical_primary_key`, `silver_table`, `gold_table`, `version`,
`sink`, `dq_overrides`) наследуется из `_base.yaml` или вычисляется.

### 4.2 Конфиг с 1–2 переопределениями

```yaml
# configs/pipelines/chembl/molecule.yaml
# ChEMBL Molecule — inherits from _base.yaml.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
schema_file: ../../schemas/chembl/molecule.yaml
description: "Extract molecules/compounds from ChEMBL API"

business_primary_keys: ["molecule_id"]

sink:
  silver:
    # Override: partition by molecule_type for efficient type-specific queries
    partition_by: ["molecule_type"]
```

### 4.3 Конфиг с максимумом переопределений (3)

```yaml
# configs/pipelines/chembl/protein_class.yaml
# ChEMBL Protein Classification — reference table.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline_name: chembl_protein_class
provider: chembl
entity_type: protein_class
schema_file: ../../schemas/chembl/protein_class.yaml
description: "ChEMBL Protein Classification hierarchy"

business_primary_keys: ["protein_class_id"]

# Override: reference table ~1.5K records, smaller batches for full load
batch_size: 500
# Override: small dataset, more frequent checkpoints
checkpoint_interval: 500

sink:
  silver:
    # Override: partition by hierarchy level for efficient tree queries
    partition_by: ["class_level"]
```

---

## 5. Целевое состояние _base.yaml (After)

```yaml
# configs/pipelines/_base.yaml
# =============================================================================
# Base Pipeline Configuration — Single Source of Truth for defaults
# =============================================================================
# All entity pipeline configs inherit from this file.
# Override only 1-3 params per entity with "# Override: <reason>" comment.
#
# DQ config: loaded from configs/quality/ hierarchy (ADR-027)
# Filter config: loaded from configs/filters/ hierarchy (ADR-028)
# Paths: auto-resolved by convention (ADR-029)
# =============================================================================

version: "1.2.0"
technical_primary_key: "entity_id"

source: {}

transform:
  steps: []

# DQ defaults: loaded from configs/quality/_defaults.yaml by DQConfigLoader.
# Do NOT duplicate thresholds here. Override per-entity via dq_overrides: {} if needed.
dq_overrides: {}

sink:
  bronze:
    format: jsonl
    save_json: true
    save_metadata: true
    dq_report:
      enabled: true
    flat_structure: true

  silver:
    format: delta
    mode: merge
    on_schema_mismatch: evolve
    save_metadata: true
    dq_report:
      enabled: true
    csv_export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"
    flat_structure: true

  gold:
    enabled: true
    format: delta
    mode: scd2
    scd_config:
      valid_from: _valid_from
      valid_to: _valid_to
      is_current: _is_current
      version: _version
    deterministic: true
    save_metadata: true
    dq_report:
      enabled: true
    csv_export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"
    flat_structure: true

maintenance:
  auto_vacuum: false
  vacuum_retention_days: 7

input_filter:
  enabled: false
  batch_size: 100
```

---

## 6. План выполнения (поэтапно)

### Phase 1: _base.yaml (SSOT)

1. Добавить `version`, `technical_primary_key` в `_base.yaml`
2. Добавить `sink.gold.mode: scd2` + `scd_config` в `_base.yaml`
3. Удалить дублирующий `dq_overrides` блок (оставить `dq_overrides: {}`)
4. Удалить `circuit_breaker` из `_base.yaml`

### Phase 2: PipelineConfigLoader (auto-compute)

5. Добавить auto-compute для `silver_table` = `{provider}_{entity_type}`
6. Добавить auto-compute для `gold_table` = `{provider}_{entity_type}`
7. Добавить default для `technical_primary_key` = `"entity_id"`
8. Добавить default для `version` из `_base.yaml`

### Phase 3: Entity configs cleanup

9. Удалить `technical_primary_key` из всех 27 entity-конфигов
10. Удалить `silver_table` / `gold_table` из всех entity-конфигов
11. Удалить `version: "1.2.0"` из конфигов где совпадает с дефолтом
12. Удалить SCD2-блоки из entity-конфигов (кроме overwrite-исключений)
13. Удалить дублирующие `flat_structure: true` (совпадает с `_base.yaml`)
14. Удалить бойлерплейт-комментарии про DQ/Filter hierarchy
15. Добавить `# Override: <reason>` ко всем оставшимся переопределениям
16. Удалить пустые секции `sink: bronze: {}` / `silver: {}` где нет overrides

### Phase 4: Тесты и валидация

17. Запустить `pytest tests/` — убедиться что ничего не сломалось
18. Запустить `pytest tests/architecture/` — проверить import boundaries
19. Проверить что `ConfigLoader.load_pipeline_config()` возвращает те же
    domain-объекты что и до рефакторинга (snapshot test)
20. Проверить каждый entity-конфиг: max 1–3 override-параметров

### Phase 5: Документация

21. Обновить CONFIG-GUIDE.md с описанием Override Policy
22. Создать ADR-03X "Config Deduplication & Override Policy"

---

## 7. Метрики успеха

| Метрика | Before | Target |
|---------|--------|--------|
| Строк YAML в pipeline-конфигах (суммарно) | ~1300 | ~400 |
| Среднее кол-во строк на entity-конфиг | ~50 | ~12 |
| Параметров с 2+ определениями | 12 | 0 |
| Max overrides в entity-конфиге | неограничено | 3 |
| Overrides без комментария | ~40 | 0 |

---

## 8. Ограничения и оговорки

- **НЕ трогать** `quality/` и `filters/` иерархии — они уже правильно
  спроектированы (ADR-027/028)
- **НЕ трогать** `sources/` — они являются SSOT для API-параметров
- **НЕ трогать** composite pipeline конфиги — у них другая структура
- **НЕ менять** семантику merge в `DQConfigLoader` / `FilterConfigLoader`
- `dq_overrides` в pipeline-конфигах (напр. `chembl/activity.yaml`)
  остаются если содержат entity-специфичные правила (не дубли _defaults)
- Auto-compute `silver_table` / `gold_table` MUST иметь fallback на
  explicit value (если задано в YAML — использовать YAML)

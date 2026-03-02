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
│   ├── -base.yaml              ← шаблон по умолчанию
│   └── {provider}/{entity}.yaml ← 27 pipeline-конфигов
├── quality/
│   ├── -defaults.yaml           ← глобальные DQ-пороги
│   ├── providers/{provider}.yaml
│   └── entities/{provider}/{entity}.yaml
├── filters/
│   ├── -defaults.yaml
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
-defaults.yaml → providers/{provider}.yaml → entities/{provider}/{entity}.yaml → inline overrides
```

---

## 2. Выявленные паттерны дублирования

### 2.1 CRITICAL — DQ-пороги дублируются в двух SSOT

**Проблема:** `soft-fail-threshold` и `hard-fail-threshold` определены одновременно в
`pipelines/-base.yaml` (строки 10–11) И в `quality/-defaults.yaml` (строки 17–18) с
идентичными значениями (0.05 / 0.20).

```yaml
# configs/pipelines/-base.yaml (строки 9-16)
dq-overrides:
  soft-fail-threshold: 0.05    # ← ДУБЛЬ
  hard-fail-threshold: 0.20    # ← ДУБЛЬ
  strict-validation: false     # ← ДУБЛЬ (то же в quality/-defaults.yaml:23)
  invalid-record-policy: "quarantine"  # ← ДУБЛЬ (то же в quality/-defaults.yaml:28)
  report:
    enabled: true              # ← ДУБЛЬ (то же в quality/-defaults.yaml:34)
    format: "json"             # ← ДУБЛЬ
    include-sample-failures: true
    sample-size: 10

# configs/quality/-defaults.yaml (строки 16-38)
thresholds:
  soft-fail: 0.05             # ← SSOT (должен быть единственным)
  hard-fail: 0.20
strict-validation: false
invalid-record-policy: quarantine
report:
  enabled: true
  format: json
  ...
```

**Риск:** При изменении порога в одном файле второй рассинхронизируется.

**Решение:** Удалить блок `dq-overrides` целиком из `-base.yaml`. DQ-параметры уже
загружаются через `DQConfigLoader` из `quality/-defaults.yaml`. Оставить только пустой
маркер:

```yaml
# configs/pipelines/-base.yaml
# DQ configuration: loaded from configs/quality/ hierarchy (ADR-027).
# Override only in entity pipeline config if needed (max 1-3 params with # Override: comment).
dq-overrides: {}
```

---

### 2.2 HIGH — SCD2-блок копипастится в 20+ файлах

**Проблема:** Идентичный блок sink.gold.scd-config повторяется дословно в 20 из 27
pipeline-конфигов:

```yaml
# Дублируется в: chembl/target, chembl/molecule, chembl/cell-line,
# chembl/compound-record, chembl/tissue, chembl/assay, pubmed/publication,
# openalex/publication, crossref/publication, semanticscholar/publication,
# uniprot/protein, uniprot/idmapping, pubchem/compound, и т.д.
gold:
  mode: scd2
  scd-config:
    valid-from: -valid-from
    valid-to: -valid-to
    is-current: -is-current
    version: -version
```

**Решение:** Вынести SCD2 как дефолт в `-base.yaml`:

```yaml
# configs/pipelines/-base.yaml
sink:
  gold:
    enabled: true
    format: delta
    mode: scd2                  # Default: SCD Type 2 for all entities
    scd-config:                 # Default SCD2 column names
      valid-from: -valid-from
      valid-to: -valid-to
      is-current: -is-current
      version: -version
    deterministic: true
    ...
```

В дочерних pipeline-конфигах SCD2-блок полностью удаляется. Исключения
(publication-similarity, publication-term — `mode: overwrite`) сохраняют ТОЛЬКО
переопределённый параметр с комментарием:

```yaml
# configs/pipelines/chembl/publication-similarity.yaml
sink:
  gold:
    # Override: similarity scores are computed fresh each run, no SCD tracking needed
    mode: overwrite
```

---

### 2.3 HIGH — flat-structure: true дублируется в publication-пайплайнах

**Проблема:** `flat-structure: true` задаётся для bronze/silver/gold в 5 publication
pipeline-конфигах (pubmed, openalex, crossref, semanticscholar, chembl/publication)
с идентичным комментарием.

```yaml
# Повторяется 5 раз:
sink:
  bronze:
    flat-structure: true  # Path already includes provider/entity
  silver:
    flat-structure: true
  gold:
    flat-structure: true
```

**Решение (вариант A — рекомендуемый):** `flat-structure: true` уже задан в `-base.yaml`
(строки 34, 48, 63). Удалить дублирующие переопределения из дочерних конфигов, так как
они идентичны дефолту.

**Решение (вариант B — если нужна категоризация):** Ввести provider-level pipeline
defaults `configs/pipelines/{provider}/-provider.yaml`, которые наследуются всеми
entity-конфигами этого провайдера. Тогда `flat-structure` задаётся один раз для
провайдера.

---

### 2.4 MEDIUM — technical-primary-key и silver/gold-table формульные

**Проблема:** Каждый pipeline-конфиг повторяет:

```yaml
technical-primary-key: "entity-id"  # Одинаков в 27 из 27 файлов
silver-table: "{provider}-{entity}" # Всегда формула от provider+entity
gold-table: "{provider}-{entity}"   # Всегда формула от provider+entity
```

**Решение:** Вынести `technical-primary-key: "entity-id"` в `-base.yaml` как дефолт.
Вычислять `silver-table` / `gold-table` автоматически из `provider` + `entity-type` в
`PipelineConfigLoader`, если не заданы явно. Удалить из всех 27 entity-конфигов.

**Изменение в коде (PipelineConfigLoader):**

```python
# В load-pipeline-config() или при сборке PipelineConfig:
if not raw-config.get("silver-table"):
    raw-config["silver-table"] = f"{provider}-{entity-type}"
if not raw-config.get("gold-table"):
    raw-config["gold-table"] = f"{provider}-{entity-type}"
if not raw-config.get("technical-primary-key"):
    raw-config["technical-primary-key"] = "entity-id"
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
#   1. configs/quality/-defaults.yaml (global defaults)
#   2. configs/quality/providers/{provider}.yaml (provider-specific)
#   3. configs/quality/entities/{provider}/{entity}.yaml (entity-specific)

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filters/-defaults.yaml (global defaults)
#   2. configs/filters/providers/{provider}.yaml (provider-specific)
#   3. configs/filters/entities/{provider}/{entity}.yaml (entity-specific)
```

**Решение:** Удалить из entity-конфигов. Задокументировать один раз в `-base.yaml`
(уже есть) и в CONFIG-GUIDE.md. В entity-конфигах оставить однострочную ссылку:

```yaml
# DQ & Filters: loaded via hierarchy (ADR-027/028/029). See -base.yaml for details.
```

---

### 2.6 MEDIUM — circuit-breaker дублируется в -base.yaml и sources

**Проблема:** `circuit-breaker` с идентичными значениями (`failure-threshold: 5`,
`recovery-timeout: 300`) определён в `pipelines/-base.yaml` И во всех
`sources/{provider}.yaml`.

**Решение:** Оставить `circuit-breaker` только в `sources/{provider}.yaml` — это
настройки устойчивости конкретного API-источника. Удалить из `-base.yaml`.

---

### 2.7 LOW — version: "1.2.0" повторяется

**Проблема:** `version: "1.2.0"` задана в 20+ pipeline-конфигах.

**Решение:** Вынести в `-base.yaml` как дефолт. Переопределять только при реальном
отличии версии конфига (publication-similarity v2.1.0 и т.д.):

```yaml
# configs/pipelines/chembl/publication-similarity.yaml
# Override: v2.1.0 schema redesign after ADR-024 naming migration
version: "2.1.0"
```

---

### 2.8 LOW — loading-strategy: full-scan-only с одинаковым комментарием

**Проблема:** `loading-strategy: full-scan-only` с комментарием про "API offset
instability" повторяется в 6 файлах (все publication + subcellular-fraction +
publication-similarity + publication-term).

**Решение:** Не является дублированием в строгом смысле (разные entity действительно
нуждаются в full-scan), но комментарий можно сократить до:

```yaml
# Override: full-scan required — API doesn't support stable incremental cursors
loading-strategy: full-scan-only
```

---

## 3. Правило переопределения (Override Policy)

### 3.1 Что разрешено переопределять в entity pipeline config

Максимум **1–3 параметра** из следующего списка:

| # | Параметр | Когда переопределять |
|---|----------|---------------------|
| 1 | `sink.gold.mode` | Если entity не использует SCD2 (напр. `overwrite`) |
| 2 | `sink.silver.partition-by` | Entity-specific партиционирование |
| 3 | `batch-size` | Если объём данных entity сильно отличается от дефолта |
| 4 | `loading-strategy` | Если entity требует `full-scan-only` |
| 5 | `page-size-override` | Если API endpoint имеет другой лимит |
| 6 | `version` | Если версия конфига отличается от дефолта |

Любой другой параметр **MUST** быть в `-base.yaml`, `quality/`, `filters/`, или `sources/`.

### 3.2 Формат комментария переопределения

Каждый переопределённый параметр **MUST** иметь комментарий в формате:

```yaml
# Override: <краткое обоснование почему значение отличается от дефолта>
parameter: value
```

Примеры:

```yaml
# Override: reference table with ~1.5K records, smaller batches for full load
batch-size: 500

# Override: similarity scores recomputed each run, no history tracking needed
mode: overwrite

# Override: smaller page size for publication endpoint (full-scan-only strategy)
page-size-override: 16

# Override: partition by molecule-type for query performance
partition-by: ["molecule-type"]
```

---

## 4. Целевое состояние pipeline-конфигов (After)

### 4.1 Минимальный конфиг (нет переопределений)

```yaml
# configs/pipelines/chembl/cell-line.yaml
# ChEMBL Cell Line — inherits all defaults from -base.yaml.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline-name: chembl-cell-line
provider: chembl
entity-type: cell-line
schema-file: ../../schemas/chembl/cell-line.yaml
description: "Extract cell lines from ChEMBL API"

business-primary-keys: ["cell-id"]
```

**Всё остальное** (`technical-primary-key`, `silver-table`, `gold-table`, `version`,
`sink`, `dq-overrides`) наследуется из `-base.yaml` или вычисляется.

### 4.2 Конфиг с 1–2 переопределениями

```yaml
# configs/pipelines/chembl/molecule.yaml
# ChEMBL Molecule — inherits from -base.yaml.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline-name: chembl-molecule
provider: chembl
entity-type: molecule
schema-file: ../../schemas/chembl/molecule.yaml
description: "Extract molecules/compounds from ChEMBL API"

business-primary-keys: ["molecule-id"]

sink:
  silver:
    # Override: partition by molecule-type for efficient type-specific queries
    partition-by: ["molecule-type"]
```

### 4.3 Конфиг с максимумом переопределений (3)

```yaml
# configs/pipelines/chembl/protein-class.yaml
# ChEMBL Protein Classification — reference table.
# DQ & Filters: loaded via hierarchy (ADR-027/028/029).

pipeline-name: chembl-protein-class
provider: chembl
entity-type: protein-class
schema-file: ../../schemas/chembl/protein-class.yaml
description: "ChEMBL Protein Classification hierarchy"

business-primary-keys: ["protein-class-id"]

# Override: reference table ~1.5K records, smaller batches for full load
batch-size: 500
# Override: small dataset, more frequent checkpoints
checkpoint-interval: 500

sink:
  silver:
    # Override: partition by hierarchy level for efficient tree queries
    partition-by: ["class-level"]
```

---

## 5. Целевое состояние -base.yaml (After)

```yaml
# configs/pipelines/-base.yaml
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
technical-primary-key: "entity-id"

source: {}

transform:
  steps: []

# DQ defaults: loaded from configs/quality/-defaults.yaml by DQConfigLoader.
# Do NOT duplicate thresholds here. Override per-entity via dq-overrides: {} if needed.
dq-overrides: {}

sink:
  bronze:
    format: jsonl
    save-json: true
    save-metadata: true
    dq-report:
      enabled: true
    flat-structure: true

  silver:
    format: delta
    mode: merge
    on-schema-mismatch: evolve
    save-metadata: true
    dq-report:
      enabled: true
    csv-export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"
    flat-structure: true

  gold:
    enabled: true
    format: delta
    mode: scd2
    scd-config:
      valid-from: -valid-from
      valid-to: -valid-to
      is-current: -is-current
      version: -version
    deterministic: true
    save-metadata: true
    dq-report:
      enabled: true
    csv-export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"
    flat-structure: true

maintenance:
  auto-vacuum: false
  vacuum-retention-days: 7

input-filter:
  enabled: false
  batch-size: 100
```

---

## 6. План выполнения (поэтапно)

### Phase 1: -base.yaml (SSOT)

1. Добавить `version`, `technical-primary-key` в `-base.yaml`
2. Добавить `sink.gold.mode: scd2` + `scd-config` в `-base.yaml`
3. Удалить дублирующий `dq-overrides` блок (оставить `dq-overrides: {}`)
4. Удалить `circuit-breaker` из `-base.yaml`

### Phase 2: PipelineConfigLoader (auto-compute)

5. Добавить auto-compute для `silver-table` = `{provider}-{entity-type}`
6. Добавить auto-compute для `gold-table` = `{provider}-{entity-type}`
7. Добавить default для `technical-primary-key` = `"entity-id"`
8. Добавить default для `version` из `-base.yaml`

### Phase 3: Entity configs cleanup

9. Удалить `technical-primary-key` из всех 27 entity-конфигов
10. Удалить `silver-table` / `gold-table` из всех entity-конфигов
11. Удалить `version: "1.2.0"` из конфигов где совпадает с дефолтом
12. Удалить SCD2-блоки из entity-конфигов (кроме overwrite-исключений)
13. Удалить дублирующие `flat-structure: true` (совпадает с `-base.yaml`)
14. Удалить бойлерплейт-комментарии про DQ/Filter hierarchy
15. Добавить `# Override: <reason>` ко всем оставшимся переопределениям
16. Удалить пустые секции `sink: bronze: {}` / `silver: {}` где нет overrides

### Phase 4: Тесты и валидация

17. Запустить `pytest tests/` — убедиться что ничего не сломалось
18. Запустить `pytest tests/architecture/` — проверить import boundaries
19. Проверить что `ConfigLoader.load-pipeline-config()` возвращает те же
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
- `dq-overrides` в pipeline-конфигах (напр. `chembl/activity.yaml`)
  остаются если содержат entity-специфичные правила (не дубли -defaults)
- Auto-compute `silver-table` / `gold-table` MUST иметь fallback на
  explicit value (если задано в YAML — использовать YAML)

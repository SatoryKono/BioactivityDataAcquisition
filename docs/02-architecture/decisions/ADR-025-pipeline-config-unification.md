# ADR-025: Pipeline Configuration Unification

**Status:** Accepted
**Date:** 2026-01-19
**Decision makers:** @BioETL-Team

## Context

Pipeline configs имели следующие проблемы:
1. Плоские пути без иерархии `{provider}/{entity}`
2. Отсутствие `sort_by` у 78% entity configs (нарушение ADR-014)
3. Нестандартные `batch_size` без документации
4. Отсутствие автоматической валидации конфигов
5. Разрозненные DQ-правила без централизации

## Decision

### 1. Единый _base.yaml (v2.0.0)

Файл `_base.yaml` является единым источником defaults для всех pipeline configs:

```
configs/
├── pipelines/
│   ├── _base.yaml           # Unified Base Schema v2.0.0 (единый источник defaults)
│   ├── _schema.json         # JSON Schema для валидации entity configs
│   ├── chembl/              # ChEMBL provider configs
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   └── ...              # 12 entity configs
│   ├── pubchem/
│   │   └── compound.yaml
│   ├── uniprot/
│   │   ├── protein.yaml
│   │   └── idmapping.yaml
│   ├── pubmed/
│   │   └── publication.yaml
│   ├── crossref/
│   │   └── publication.yaml
│   ├── openalex/
│   │   └── publication.yaml
│   ├── semanticscholar/
│   │   └── publication.yaml
│   └── composite/           # Composite pipelines (ADR-026)
│       ├── publication.yaml
│       └── target.yaml
├── sources/
│   └── <provider>.yaml      # Provider-level API settings (7 файлов)
└── dq/
    ├── _defaults.yaml       # Global DQ defaults
    ├── providers/           # Provider-level DQ rules
    └── entities/            # Entity-level DQ rules
```

**Rationale**: Единый источник defaults устраняет рассинхронизацию. Entity configs наследуют от `_base.yaml` и переопределяют только entity-specific поля.

### 2. Иерархические пути для данных

Введён стандартный паттерн путей:

```
data/output/{layer}/{provider}/{entity}/
```

| Слой | Паттерн | Пример |
|------|---------|--------|
| Bronze | `data/output/bronze/{provider}/{entity}/` | `data/output/bronze/chembl/activity/` |
| Silver | `data/output/silver/{provider}/{entity}/` | `data/output/silver/chembl/activity/` |
| Gold | `data/output/gold/{provider}/{entity}/` | `data/output/gold/chembl/activity/` |

**Bronze file layout (contract):**
```
data/output/bronze/{provider}/{entity}/{YYYY-MM-DD}/{filename}.jsonl.zst
```

**CSV Export** использует тот же путь, что и Delta:
```yaml
csv_export:
  path: "data/output/silver/chembl/activity"  # Рядом с Delta таблицей
```

**Rationale**: Консистентная структура упрощает навигацию и автоматизацию.

### 3. Обязательный sort_by (ADR-014 compliance)

**MUST**: Все entity configs содержат `sort_by` для Silver и Gold слоёв:

```yaml
sink:
  silver:
    path: "data/output/silver/chembl/activity"
    primary_key: ["activity_id"]
    sort_by:
      columns: ["activity_id"]
      ascending: true
  gold:
    path: "data/output/gold/chembl/activity"
    sort_by:
      columns: ["activity_id"]
      ascending: true
```

**Статус**: Все 21 entity configs содержат `sort_by` для обоих слоёв (верифицировано 2026-02-03). Composite pipelines (5) используют отдельную схему (ADR-026).

**Rationale**: Детерминизм выходных данных, воспроизводимость результатов.

### 4. JSON Schema валидация

Файл `configs/pipelines/_schema.json` (v2.0) проверяет entity configs:

```bash
# Валидация всех конфигов
python scripts/validate_pipeline_configs.py
```

Schema проверяет:
- **Обязательные поля**: `pipeline_name`, `provider`, `entity_type`, `version`, `primary_keys`, `silver_table`, `gold_table`, `sink`
- **Формат `pipeline_name`**: `^[a-z]+_[a-z_]+$`
- **Допустимые `provider`**: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`
- **Структура `sink`**: обязательные `bronze.path`, `silver.path`, `silver.primary_key`, `gold.path`
- **Формат `version`**: Semantic versioning `^\d+\.\d+\.\d+$`

### 5. Naming Conventions

| Элемент | Паттерн | Пример |
|---------|---------|--------|
| `pipeline_name` | `<provider>_<entity>` | `chembl_activity` |
| `silver_table` | `<provider>_<entity>` | `chembl_activity` |
| `gold_table` | `<provider>_<entity>` | `chembl_activity` |
| Config path | `configs/pipelines/<provider>/<entity>.yaml` | `configs/pipelines/chembl/activity.yaml` |

**Статус**: Консистентность по всем 19 entity configs + 2 composite (верифицировано 2026-02-03).

### 6. Source Config Separation

Provider-level API settings вынесены в `configs/sources/<provider>.yaml`:

```yaml
# configs/sources/chembl.yaml
source:
  type: api
  load_strategy: full
  batch_size: 20
  provider_config:
    base_url: https://www.ebi.ac.uk/chembl/api/data
    auth_type: public
  rate_limit:
    requests_per_second: 5
    burst: 10
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
```

Entity configs ссылаются через `source_file`:
```yaml
# configs/pipelines/chembl/activity.yaml
source_file: ../../sources/chembl.yaml
```

**Провайдеры с source configs**: chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar (7 файлов).

### 7. Hierarchical DQ Configuration (ADR-027)

DQ-правила загружаются иерархически через `DQConfigLoader`:

```
configs/quality/
├── _defaults.yaml                    # Global defaults
├── providers/<provider>.yaml         # Provider-level rules
└── entities/<provider>/<entity>.yaml # Entity-level rules
```

Entity configs могут:
1. Ссылаться на DQ файл: `dq_config_file: ../../dq/entities/chembl/activity.yaml`
2. Определять inline правила в `dq_overrides:`
3. Комбинировать оба подхода (inline overrides поверх файла)

```yaml
# configs/pipelines/chembl/activity.yaml
dq_config_file: ../../dq/entities/chembl/activity.yaml

dq_overrides:
  field_validations:
    - field: "activity_id"
      type: "range"
      min: 1
      nullable: false
```

## Consequences

### Positive

1. **Единый источник defaults**: `_base.yaml` v2.0.0 — нет дублирования
2. **Детерминизм выходных данных**: `sort_by` во всех 19 entity configs (ADR-014)
3. **Автоматическая валидация**: JSON Schema (`_schema.json`) валидирует структуру
4. **Консистентные пути**: `{layer}/{provider}/{entity}` упрощает навигацию
5. **Provider knowledge captured**: API limits, auth requirements в source configs
6. **Иерархические DQ правила**: Централизация через `configs/quality/` (ADR-027)
7. **Separation of concerns**: Source configs отделены от pipeline configs

### Negative

1. **Увеличенная сложность DQ**: Иерархическая загрузка требует понимания приоритетов
   - Mitigated: Документация в ADR-027, явный порядок merge

### Neutral

1. **19 entity configs + 2 composite**: Все используют единый формат и наследование от `_base.yaml`
2. **7 source configs**: Один на провайдера, DRY для API settings

## Alternatives Considered

### A. YAML Anchors for Inheritance

Use YAML anchors/aliases for config inheritance:
```yaml
<<: *defaults
pipeline_name: chembl_activity
```

**Rejected**: Requires multi-file anchor resolution. Current file-based inheritance через `_base.yaml` проще и поддерживается стандартными инструментами.

### B. Плоские пути без иерархии

Оставить пути вида `data/output/bronze/` без `{provider}/{entity}`.

**Rejected**: Сложно навигировать при 21 pipelines, нет группировки по провайдерам.

### C. Inline DQ rules only

Все DQ правила только в pipeline configs, без иерархической системы.

**Rejected**: Дублирование provider-level правил (например, CHEMBL ID pattern) между entity configs. Иерархическая система (`configs/quality/`) позволяет DRY.

### D. Provider configs внутри pipelines/

Хранить source configs в `configs/pipelines/_providers/`.

**Rejected**: Смешивание concerns. `configs/sources/` явно отделяет API settings от pipeline логики.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| `sink.silver.format: delta` | ✅ PASS | All configs inherit from `_base.yaml` |
| `sink.silver.primary_key` | ✅ PASS | All 19 entity configs specify (auto-propagated) |
| `sink.silver.sort_by` | ✅ PASS | All 19 entity configs (ADR-014, auto-propagated from primary_keys) |
| `sink.gold.sort_by` | ✅ PASS | All 19 entity configs (ADR-014, auto-propagated from primary_keys) |
| `dq_overrides` thresholds | ✅ PASS | 0.05/0.20 in `_base.yaml` defaults |
| `circuit_breaker` settings | ✅ PASS | 5/300 in `_base.yaml` and source configs |
| `rate_limit` per provider | ✅ PASS | In 7 source configs |
| No hardcoded secrets | ✅ PASS | Uses `${ENV_VAR}` syntax where needed |
| `pipeline_name` format | ✅ PASS | All match `^[a-z]+_[a-z_]+$` |
| Hierarchical paths | ✅ PASS | All use `{layer}/{provider}/{entity}` |

## References

- [RULES.md v5.18, Appendix D](../../RULES.md) - Reference schema
- [ADR-014: Deterministic Writes](ADR-014-deterministic-writes.md) - sort_by requirement
- [ADR-027: DQ Rules Externalization](ADR-027-dq-rules-externalization.md) - Hierarchical DQ config
- [03-file-policy.md](../../00-project-rules/03-file-policy.md) - File structure documentation
- [04-extending-bioetl.md](../../00-project-rules/04-extending-bioetl.md) - Entity config template
- [configs/pipelines/_base.yaml](../../../configs/pipelines/_base.yaml) - Unified Base Schema v2.0.0
- [configs/pipelines/_schema.json](../../../configs/pipelines/_schema.json) - JSON Schema v2.0

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-13 | Claude Code | Initial version |
| 2026-01-14 | Claude Code | Added: Hierarchical paths `{layer}/{provider}/{entity}` |
| 2026-01-14 | Claude Code | Added: Mandatory `sort_by` for ADR-014 compliance |
| 2026-01-14 | Claude Code | Added: JSON Schema validation via `_schema.json` |
| 2026-01-19 | Claude Code | Fixed: Corrected file structure (`_base.yaml` is the defaults file, not `_defaults.yaml`) |
| 2026-01-19 | Claude Code | Added: Source config separation (`configs/sources/`) |
| 2026-01-19 | Claude Code | Added: Hierarchical DQ configuration reference (ADR-027) |
| 2026-01-19 | Claude Code | Updated: Compliance matrix with verification status |
| 2026-02-03 | Claude Code | Fixed: Config counts (19 entity + 2 composite = 21 total) |
| 2026-02-03 | Claude Code | Added: Reference to ADR-026 for composite pipelines |
| 2026-02-03 | Claude Code | Fixed: ChEMBL has 12 entity configs, pubmed uses publication.yaml |

______________________________________________________________________

Version: 1.0.0
Status: Accepted (partially superseded by ADR-039)
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-025: Pipeline Configuration Unification

**Date:** 2026-01-19
**Status:** Accepted (partially superseded by ADR-039)
**Decision makers:** @BioETL-Team
**Superseded by:** [ADR-039](ADR-039-unified-entity-config-format.md) (partial supersede: canonical config layout and active path model)

## Context

Pipeline configs имели следующие проблемы:

1. Плоские пути без иерархии `{provider}/{entity}`
1. Отсутствие `sort-by` у 78% entity configs (нарушение ADR-014)
1. Нестандартные `batch-size` без документации
1. Отсутствие автоматической валидации конфигов
1. Разрозненные DQ-правила без централизации

## Decision

### 1. Единый \_base.yaml (v2.0.0)

Файл `_base.yaml` является единым источником defaults для всех pipeline configs:

```
configs/
├── pipelines/
│   ├── _base.yaml           # Unified Base Schema v2.0.0 (единый источник defaults)
│   ├── chembl/              # ChEMBL provider configs
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   └── ...              # 14 entity configs
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
│       ├── activity.yaml
│       ├── assay.yaml
│       ├── molecule.yaml
│       ├── publication.yaml
│       └── target.yaml
├── sources/
│   └── <provider>.yaml      # Provider-level API settings (7 файлов)
└── quality/
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

| Слой   | Паттерн                                   | Пример                                |
| ------ | ----------------------------------------- | ------------------------------------- |
| Bronze | `data/output/bronze/{provider}/{entity}/` | `data/output/bronze/chembl/activity/` |
| Silver | `data/output/silver/{provider}/{entity}/` | `data/output/silver/chembl/activity/` |
| Gold   | `data/output/gold/{provider}/{entity}/`   | `data/output/gold/chembl/activity/`   |

**Bronze file layout (contract):**

```
data/output/bronze/{provider}/{entity}/{YYYY-MM-DD}/{filename}.jsonl.zst
```

**CSV Export** использует тот же путь, что и Delta:

```yaml
csv-export:
  path: "data/output/silver/chembl/activity"  # Рядом с Delta таблицей
```

**Rationale**: Консистентная структура упрощает навигацию и автоматизацию.

### 3. Обязательный sort-by (ADR-014 compliance)

**MUST**: Все entity configs содержат `sort-by` для Silver и Gold слоёв:

```yaml
sink:
  silver:
    path: "data/output/silver/chembl/activity"
    primary-key: ["activity-id"]
    sort-by:
      columns: ["activity-id"]
      ascending: true
  gold:
    path: "data/output/gold/chembl/activity"
    sort-by:
      columns: ["activity-id"]
      ascending: true
```

**Статус**: Все 21 entity configs содержат `sort-by` для обоих слоёв (верифицировано 2026-02-03). Composite pipelines (5) используют отдельную схему (ADR-026).

**Rationale**: Детерминизм выходных данных, воспроизводимость результатов.

### 4. Pydantic Schema валидация

Валидация entity configs выполняется Pydantic-схемами в `src/bioetl/infrastructure/schemas/pipeline_config.py`:

```bash
# Валидация всех конфигов
python scripts/schema/validation/validate_pipeline_configs.py
```

Schema проверяет:

- **Обязательные поля**: `pipeline-name`, `provider`, `entity_type`, `version`, `primary-keys`, `silver-table`, `gold-table`, `sink`
- **Формат `pipeline-name`**: `^[a-z]+-[a-z-]+$`
- **Допустимые `provider`**: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`
- **Структура `sink`**: обязательные `bronze.path`, `silver.path`, `silver.primary-key`, `gold.path`
- **Формат `version`**: Semantic versioning `^\d+\.\d+\.\d+$`

### 5. Naming Conventions

| Элемент         | Паттерн                                     | Пример                                  |
| --------------- | ------------------------------------------- | --------------------------------------- |
| `pipeline-name` | `<provider>-<entity>`                       | `chembl_activity`                       |
| `silver-table`  | `<provider>-<entity>`                       | `chembl_activity`                       |
| `gold-table`    | `<provider>-<entity>`                       | `chembl_activity`                       |
| Config path     | `configs/entities/<provider>/<entity>.yaml` | `configs/entities/chembl/activity.yaml` |

**Статус**: Консистентность по всем 21 entity configs + 5 composite (верифицировано 2026-02-17).

### 6. Source Config Separation

Provider-level API settings вынесены в `configs/providers/<provider>.yaml`:

```yaml
# configs/providers/chembl.yaml
source:
  type: api
  load-strategy: full
  batch-size: 20
  provider-config:
    base-url: https://www.ebi.ac.uk/chembl/api/data
    auth-type: public
  rate-limit:
    requests-per-second: 5
    burst: 10
  circuit-breaker:
    failure-threshold: 5
    recovery-timeout: 300
```

Entity configs ссылаются через `source-file`:

```yaml
# configs/entities/chembl/activity.yaml
source-file: ../../providers/chembl.yaml
```

**Провайдеры с source configs**: chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar (7 файлов).

### 7. Hierarchical DQ Configuration (ADR-027)

DQ-правила загружаются иерархически через `DQConfigLoader`:

```
configs/
├── base/quality.yaml                      # Global defaults
├── providers/<provider>.yaml#quality      # Provider-level rules
└── entities/<provider>/<entity>.yaml#quality # Entity-level rules
```

Entity configs могут:

1. Ссылаться на DQ файл: `dq-config-file: ../../entities/chembl/activity.yaml`
1. Определять inline правила в `dq-overrides:`
1. Комбинировать оба подхода (inline overrides поверх файла)

```yaml
# configs/entities/chembl/activity.yaml
dq-config-file: ../../entities/chembl/activity.yaml

dq-overrides:
  field-validations:
    - field: "activity-id"
      type: "range"
      min: 1
      nullable: false
```

## Consequences

### Positive

1. **Единый источник defaults**: `_base.yaml` v2.0.0 — нет дублирования
1. **Детерминизм выходных данных**: `sort-by` во всех 21 entity configs (ADR-014)
1. **Автоматическая валидация**: Pydantic schemas валидируют структуру
1. **Консистентные пути**: `{layer}/{provider}/{entity}` упрощает навигацию
1. **Provider knowledge captured**: API limits, auth requirements в source configs
1. **Иерархические DQ правила**: Централизация через unified hierarchy (`configs/base|providers|entities`) (ADR-027)
1. **Separation of concerns**: Source configs отделены от pipeline configs

### Negative

1. **Увеличенная сложность DQ**: Иерархическая загрузка требует понимания приоритетов
   - Mitigated: Документация в ADR-027, явный порядок merge

### Neutral

1. **21 entity configs + 5 composite**: Все используют единый формат и наследование от `_base.yaml`
1. **7 source configs**: Один на провайдера, DRY для API settings

## Alternatives Considered

### A. YAML Anchors for Inheritance

Use YAML anchors/aliases for config inheritance:

```yaml
<<: *defaults
pipeline-name: chembl_activity
```

**Rejected**: Requires multi-file anchor resolution. Current file-based inheritance через `_base.yaml` проще и поддерживается стандартными инструментами.

### B. Плоские пути без иерархии

Оставить пути вида `data/output/bronze/` без `{provider}/{entity}`.

**Rejected**: Сложно навигировать при 21 pipelines, нет группировки по провайдерам.

### C. Inline DQ rules only

Все DQ правила только в pipeline configs, без иерархической системы.

**Rejected**: Дублирование provider-level правил (например, CHEMBL ID pattern) между entity configs. Иерархическая система unified DQ-секций позволяет DRY.

### D. Provider configs внутри pipelines/

Хранить source configs в `configs/entities/-providers/`.

**Rejected**: Смешивание concerns. `configs/providers/` явно отделяет API settings от pipeline логики.

## Compliance

| Requirement                 | Status  | Notes                                                              |
| --------------------------- | ------- | ------------------------------------------------------------------ |
| `sink.silver.format: delta` | ✅ PASS | All configs inherit from `_base.yaml`                              |
| `sink.silver.primary-key`   | ✅ PASS | All 21 entity configs specify (auto-propagated)                    |
| `sink.silver.sort-by`       | ✅ PASS | All 21 entity configs (ADR-014, auto-propagated from primary-keys) |
| `sink.gold.sort-by`         | ✅ PASS | All 21 entity configs (ADR-014, auto-propagated from primary-keys) |
| `dq-overrides` thresholds   | ✅ PASS | 0.05/0.20 in `_base.yaml` defaults                                 |
| `circuit-breaker` settings  | ✅ PASS | 5/300 in `_base.yaml` and source configs                           |
| `rate-limit` per provider   | ✅ PASS | In 7 source configs                                                |
| No hardcoded secrets        | ✅ PASS | Uses `${ENV-VAR}` syntax where needed                              |
| `pipeline-name` format      | ✅ PASS | All match `^[a-z]+-[a-z-]+$`                                       |
| Hierarchical paths          | ✅ PASS | All use `{layer}/{provider}/{entity}`                              |

## References

- [RULES.md v6.1, Appendix D](../../00-project/RULES.md) - Reference schema
- [ADR-014: Deterministic Writes](ADR-014-deterministic-writes.md) - sort-by requirement
- [ADR-027: DQ Rules Externalization](ADR-027-dq-rules-externalization.md) - Hierarchical DQ config
- [03-file-policy.md](../../00-project/governance/03-file-policy.md) - File structure documentation
- [04-extending-bioetl.md](../../00-project/governance/04-extending-bioetl.md) - Entity config template
- [configs/base/pipeline.yaml](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/configs/base/pipeline.yaml) - Unified Base Schema v2.0.0
- [Pipeline Pydantic Schema](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/src/bioetl/infrastructure/schemas/pipeline_config.py) - Pydantic validation schema

## Changelog

| Date       | Author      | Change                                                                                                                                                                                                                   |
| ---------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-01-13 | Claude Code | Initial version                                                                                                                                                                                                          |
| 2026-01-14 | Claude Code | Added: Hierarchical paths `{layer}/{provider}/{entity}`                                                                                                                                                                  |
| 2026-01-14 | Claude Code | Added: Mandatory `sort-by` for ADR-014 compliance                                                                                                                                                                        |
| 2026-01-14 | Claude Code | Added: JSON Schema validation via `_schema.json`                                                                                                                                                                         |
| 2026-01-19 | Claude Code | Fixed: Corrected file structure (`_base.yaml` is the defaults file, not `_defaults.yaml`)                                                                                                                                |
| 2026-01-19 | Claude Code | Added: Source config separation (`configs/providers/`)                                                                                                                                                                   |
| 2026-01-19 | Claude Code | Added: Hierarchical DQ configuration reference (ADR-027)                                                                                                                                                                 |
| 2026-01-19 | Claude Code | Updated: Compliance matrix with verification status                                                                                                                                                                      |
| 2026-02-03 | Claude Code | Fixed: Config counts (19 entity + 2 composite = 21 total)                                                                                                                                                                |
| 2026-02-03 | Claude Code | Added: Reference to ADR-026 for composite pipelines                                                                                                                                                                      |
| 2026-02-03 | Claude Code | Fixed: ChEMBL has 12 entity configs, pubmed uses publication.yaml                                                                                                                                                        |
| 2026-02-17 | Claude Code | Fixed: Config counts (21 entity + 5 composite), ChEMBL has 14 entity configs                                                                                                                                             |
| 2026-02-17 | Claude Code | Fixed: DQ path `configs/dq/` migrated to hierarchical DQ configs (ADR-027)                                                                                                                                               |
| 2026-02-17 | Claude Code | Fixed: Removed `_schema.json` reference (validation via Pydantic schemas)                                                                                                                                                |
| 2026-02-17 | Claude Code | Fixed: Composite directory listing (activity, assay, molecule, publication, target)                                                                                                                                      |
| 2026-02-24 | Claude Code | Superseded (partially): Entity configs consolidated into unified format (see ADR-039). Config path `configs/entities/{p}/{e}.yaml` replaced by `configs/entities/{p}/{e}.yaml`. Legacy directories removed (RF-CFG-035). |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.

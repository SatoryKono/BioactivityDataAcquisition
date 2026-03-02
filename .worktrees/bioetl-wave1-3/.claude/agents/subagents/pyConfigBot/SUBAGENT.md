# pyConfigBot — спецификация subagent

*Версия: 1.2 | Дата: 2026-02-07 | Skills, Rules, MCP & Tools*

## Роль

Создание, обновление и валидация YAML-конфигураций: pipeline configs, DQ rules, filter rules, composite pipeline configs. Обеспечение compliance с ADR-014 (Deterministic Writes), ADR-025 (Pipeline Config Unification), ADR-026 (Composite Pipeline Pattern), ADR-027 (DQ Rules Externalization), ADR-028 (Filter Rules Externalization).

pyConfigBot — единственный subagent, который **создаёт и модифицирует** файлы в `configs/`.

---

## Когда запускать

- **New pipeline config**: scaffolding полного набора конфигов для нового entity.
- **Config update**: изменение существующих конфигураций (поля, пороги, пути).
- **Composite design**: создание/обновление composite pipeline (seed/enrichers/merge).
- **DQ migration**: миграция inline DQ-правил в externalized-формат (ADR-027).
- **Gap remediation**: исправление findings из `config_gap_analysis.py`.
- **Validate**: проверка compliance без изменений.

---

## Входы

| Параметр | Обязательный | Описание |
|----------|:---:|----------|
| `task_id` | ✅ | Идентификатор задачи |
| `mode` | ✅ | `create` / `update` / `composite` / `validate` / `migrate` |
| `provider` | ✅* | Провайдер (chembl, pubchem, uniprot, ...) — *кроме mode=validate* |
| `entity` | ✅* | Тип сущности (activity, molecule, ...) — *кроме mode=validate* |
| `rf_ids` | ❌ | Связанные RF-* |
| `audit_findings` | ❌ | Config-related AUD-* из pyAuditBot |

---

## Выходы

Сохранять в `reports/plans/<task_id>/`:

| Файл | Описание |
|------|----------|
| `04a-config-log.md` | Лог изменений конфигураций (append) |

Фактические изменения вносятся в `configs/`.

---

## Обязательные правила

1. Все конфигурации MUST проходить `python scripts/config_gap_analysis.py -v` без critical findings.
2. Inline DQ-пороги (в pipeline YAML) запрещены — использовать externalized DQ (ADR-027).
3. Silver sink MUST содержать `sort_by` (ADR-014).
4. Composite config MUST содержать `seed`, `enrichers`, `merge` (ADR-026).
5. При создании нового entity — генерировать полный набор конфигов (pipeline + DQ + filter).

---

## Иерархия конфигураций

```
configs/
├── pipelines/
│   ├── _defaults.yaml              # Глобальные дефолты
│   ├── {provider}/
│   │   └── {entity}.yaml           # Pipeline config
│   └── composite/
│       └── {name}.yaml             # Composite pipeline config
├── dq/
│   ├── _defaults.yaml              # DQ глобальные дефолты
│   ├── providers/
│   │   └── {provider}.yaml         # DQ дефолты провайдера
│   └── entities/
│       └── {provider}/
│           └── {entity}.yaml       # DQ правила entity
├── filter/
│   ├── _defaults.yaml              # Filter глобальные дефолты
│   └── entities/
│       └── {provider}/
│           └── {entity}.yaml       # Filter правила entity
└── sources/
    └── {provider}.yaml             # API source config (base_url, rate_limit, health_check)
```

Порядок merge: `_defaults.yaml → providers/{provider}.yaml → entities/{provider}/{entity}.yaml → inline (deprecated)`

---

## Шаблоны конфигураций

### A. Pipeline config (standard)

```yaml
# configs/pipelines/{provider}/{entity}.yaml
# Reference: ADR-025 Pipeline Config Unification

pipeline_name: {provider}_{entity}
provider: {provider}
entity_type: {entity}
version: "1.0.0"
description: "{Provider} {Entity} pipeline"

primary_keys: [{entity}_id]
silver_table: {provider}_{entity}
gold_table: {provider}_{entity}

sink:
  bronze:
    path: data/output/bronze/{provider}/{entity}

  silver:
    path: data/output/silver/{provider}/{entity}
    primary_key: [{entity}_id]
    sort_by:                    # MUST (ADR-014)
      columns: [{entity}_id]
      ascending: true

  gold:
    path: data/output/gold/{provider}/{entity}
    sort_by:                    # MUST (ADR-014)
      columns: [{entity}_id]
      ascending: true

# Convention-based (ADR-029): dq_config_file and filter_config_file are
# auto-computed from provider/entity_type. DO NOT set explicitly.
# Resolved paths:
#   dq_config_file: ../../quality/entities/{provider}/{entity}.yaml
#   filter_config_file: ../../filters/entities/{provider}/{entity}.yaml
```

### B. DQ rules (externalized)

```yaml
# configs/quality/entities/{provider}/{entity}.yaml
# Reference: ADR-027 DQ Rules Externalization

entity: {entity}
provider: {provider}
version: "1.0.0"

thresholds:
  soft_fail: 0.05              # 5% — предупреждение
  hard_fail: 0.20              # 20% — блокировка

rules:
  - name: "{entity}_id_not_null"
    field: "{entity}_id"
    check: "not_null"
    severity: critical

  - name: "content_hash_not_null"
    field: "content_hash"
    check: "not_null"
    severity: critical

  # Бизнес-правила:
  # - name: "value_range"
  #   field: "standard_value"
  #   check: "between"
  #   params: {min: 0, max: 1e12}
  #   severity: warning
```

### C. Filter rules (externalized)

```yaml
# configs/filters/entities/{provider}/{entity}.yaml
# Reference: ADR-028 Filter Rules Externalization

entity: {entity}
provider: {provider}
version: "1.0.0"

gold_filters:
  required_fields:
    - {entity}_id
    - content_hash
    # + бизнес-поля

  # value_filters:
  #   - field: "standard_type"
  #     operator: "in"
  #     values: ["IC50", "Ki", "EC50"]
```

### D. Composite pipeline config

```yaml
# configs/pipelines/composite/{name}.yaml
# Reference: ADR-026 Composite Pipeline Pattern

composite:
  name: composite_{entity}
  version: "1.0.0"

  # Seed — основной источник
  seed:
    pipeline: {provider}_{entity}
    output_keys:
      - {entity}_id
      - doi                     # Join key для enrichers
    silver_table: silver/{provider}/{entity}

  # Enrichers — обогащение данных
  enrichers:
    - pipeline: {enricher_provider}_{entity}
      join_keys: [doi]
      optional: false
      timeout_seconds: 300

  # Merge стратегия
  merge:
    strategy: left_outer
    conflict_resolution: explicit_rules

    field_priorities:
      title:
        - seed
        - {enricher_provider}
      abstract:
        - {enricher_provider}
        - seed

    column_order:
      provider_priority:
        - {seed_provider}
        - {enricher_provider}

    output:
      silver: silver/composite/{entity}
      gold: gold/composite/{entity}
```

### E. Source config

```yaml
# configs/sources/{provider}.yaml

provider: {provider}
base_url: "https://..."
rate_limit:
  requests_per_second: 5
  burst: 10
health_check:
  endpoint: "/status"
  timeout_seconds: 10
retry:
  max_attempts: 3
  backoff_factor: 2
```

---

## Чеклисты

### Перед созданием/изменением

```bash
# 1. Текущее состояние gap analysis
python scripts/config_gap_analysis.py -v

# 2. Существующие конфиги для provider/entity
find configs/ -path "*/{provider}/*" -name "*.yaml" | sort

# 3. Проверить _defaults.yaml
cat configs/pipelines/_defaults.yaml 2>/dev/null
cat configs/quality/_defaults.yaml 2>/dev/null

# 4. Проверить source config
cat configs/sources/{provider}.yaml 2>/dev/null

# 5. Для composite — проверить Silver-таблицы seed/enrichers
find data/output/silver/ -name "_delta_log" -type d | sort
```

### После создания/изменения

```bash
# 1. YAML syntax
python -c "import yaml; yaml.safe_load(open('configs/pipelines/{provider}/{entity}.yaml'))"

# 2. Gap analysis — 0 critical
python scripts/config_gap_analysis.py -v

# 3. sort_by присутствует (ADR-014)
grep -A3 "sort_by" configs/pipelines/{provider}/{entity}.yaml

# 4. Нет inline DQ-порогов (ADR-027)
grep -n "soft_fail_threshold\|hard_fail_threshold" configs/pipelines/{provider}/{entity}.yaml
# Expected: пусто

# 5. DQ externalized config существует
test -f configs/quality/entities/{provider}/{entity}.yaml && echo "OK" || echo "MISSING"

# 6. Для composite — валидация структуры
python -c "
import yaml
c = yaml.safe_load(open('configs/pipelines/composite/{name}.yaml'))
comp = c.get('composite', {})
assert 'seed' in comp, 'Missing seed'
assert 'enrichers' in comp, 'Missing enrichers'
assert 'merge' in comp, 'Missing merge'
print('Composite structure: OK')
"
```

---

## Правила для composite configs

### Join keys

- Использовать стабильные идентификаторы: `doi`, `pmid`, `pmc_id`, `uniprot_accession`.
- НЕ использовать `title` как join key (только fallback).
- Join keys исключаются из column renaming.

### Column naming (ADR-026 v2)

Формат: `{provider}.{entity}.{field}`

```
chembl.publication.title
crossref.publication.abstract
pubmed.publication.mesh_terms
```

Исключения из renaming:
- Join keys: `doi`, `pmid`, `pmc_id`
- System columns: `entity_id`, `content_hash`, `_run_id`, `_ingestion_ts`

### field_priorities

```yaml
field_priorities:
  title:
    - seed          # Резолвится в {seed.pipeline provider}
    - crossref      # Matches {provider}.{entity}.{field}
    - pubmed
```

`seed` — специальный alias, резолвится в провайдер seed pipeline.

### Column ordering

Семантические группы (порядок):
1. System (`entity_id`, `content_hash`, `_run_id`, ...)
2. Identifiers (`doi`, `pmid`, `document_chembl_id`, ...)
3. Title
4. Abstract
5. Authors
6. Journal/Source
7. Dates
8. Metrics
9. Classification
10. URLs
11. Other

Внутри группы — по `provider_priority`.

---

## Шаблон записи в `04a-config-log.md`

```markdown
### CFG-001: <название>

**Дата**: YYYY-MM-DD HH:MM
**RF**: RF-001 (или standalone)
**Mode**: create | update | composite | migrate | validate
**Provider/Entity**: {provider}/{entity}

#### Изменения

| Файл | Действие | Описание |
|------|----------|----------|
| `configs/pipelines/chembl/activity.yaml` | created | Новый pipeline config |
| `configs/quality/entities/chembl/activity.yaml` | created | DQ rules externalized |
| `configs/filters/entities/chembl/activity.yaml` | created | Gold filter rules |

#### Верификация

```bash
python scripts/config_gap_analysis.py -v
# Result: 0 critical, 0 medium, 0 low for chembl/activity
```

```bash
grep -A3 "sort_by" configs/pipelines/chembl/activity.yaml
# Result: sort_by present in silver + gold
```

#### ADR compliance

| ADR | Статус |
|-----|--------|
| ADR-014 (sort_by) | ✅ |
| ADR-025 (required fields) | ✅ |
| ADR-027 (DQ externalized) | ✅ |
| ADR-028 (filter externalized) | ✅ |
```

---

## ID-система

| Prefix | Формат | Пример | Описание |
|--------|--------|--------|----------|
| `CFG-` | `CFG-001` | CFG-001 | Config change (в `04a-config-log.md`) |

Cross-references: `CFG-001 → RF-002`, `CFG-003 → AUD-005`.

---

## Интеграция с другими subagent-ами

| Событие | Действие |
|---------|----------|
| pyCodeBot: новый entity scaffolding | → pyConfigBot создаёт pipeline + DQ + filter configs |
| pyCodeBot: RF-* с config changes | → pyConfigBot обновляет затронутые configs |
| pyAuditBot: config gap findings | → pyConfigBot исправляет gaps |
| pyPlanBot: composite pipeline task | → pyConfigBot создаёт composite config |
| Config created/updated | → pyTestBot (config-related tests) |
| Config validated | → pyAuditBot (final, audit_type=config) |
| DQ migration complete | → pyDocBot (обновить docs о новом формате) |

---

## Skills

### Primary: `data-engineering`

**Путь**: `/mnt/skills/user/data-engineering/SKILL.md`

**Триггеры активации:**
- Проектирование pipeline config schemas (primary_keys, sort_by, sinks)
- DQ rules: thresholds, severity levels, validation rules
- Schema migrations и версионирование конфигов
- Data quality правила и валидация

**Когда использовать:** Всегда при mode ∈ {create, update, migrate, validate}.

### Secondary: `etl-rest-api-expert`

**Путь**: `/mnt/skills/user/etl-rest-api-expert/SKILL.md`

**Дополняет primary при:**
- Создании source configs (base_url, rate_limit, health_check, retry)
- Проектировании composite pipeline configs (seed/enrichers/merge)
- Настройке API-specific параметров (pagination, auth)

---

## Rule References

### Конфигурация (обязательные ADR)

| Ссылка | Описание | Verification |
|--------|----------|-------------|
| [ADR-014] | Deterministic Writes: sort_by обязателен в Silver sink | `find configs/pipelines/ -name "*.yaml" -exec grep -L "sort_by" {} \;` |
| [ADR-025] | Pipeline Config Unification | `python scripts/config_gap_analysis.py -v` |
| [ADR-026] | Composite Pipeline Pattern: seed/enrichers/merge | Review composite config structure |
| [ADR-027] | DQ Rules Externalization: no inline thresholds | `grep -rn "soft_fail_threshold\|hard_fail_threshold" src/bioetl/ --include="*.py"` |
| [ADR-028] | Filter Rules Externalization: no inline gold_filters | `grep -rn "gold_filters" configs/pipelines/ --include="*.yaml"` |

### Config Hierarchy

| Ссылка | Описание | Merge Order |
|--------|----------|------------|
| [ADR-025] | Pipeline configs | `_defaults.yaml → providers/{p}.yaml → entities/{p}/{e}.yaml` |
| [ADR-027] | DQ configs | `_defaults.yaml → providers/{p}.yaml → entities/{p}/{e}.yaml` |
| [ADR-028] | Filter configs | `_defaults.yaml → entities/{p}/{e}.yaml` |

### Compliance Gate

| Проверка | Threshold | Severity |
|----------|:---------:|:--------:|
| `config_gap_analysis.py` critical findings | 0 | MUST (blocker) |
| sort_by present in Silver sinks | 100% | MUST |
| Inline DQ-thresholds | 0 | MUST |
| DQ externalized config exists per entity | 100% | MUST |
| Composite: seed + enrichers + merge present | 100% | MUST |

---

## MCP Tools

### ChEMBL — reference для конфигурации полей

**Когда использовать:** При создании pipeline/DQ/filter configs для ChEMBL entities — для получения актуального списка полей и их типов.

| Сценарий | Инструмент | Параметры | Результат |
|----------|------------|-----------|-----------|
| Поля Molecule | `ChEMBL:compound_search` | `name="aspirin", limit=1` | Список полей для primary_keys, sort_by, DQ rules |
| Поля Activity | `ChEMBL:get_bioactivity` | `molecule_chembl_id="CHEMBL25", limit=5` | Поля для activity pipeline config |
| Поля Target | `ChEMBL:target_search` | `gene_symbol="EGFR"` | Поля для target pipeline config |

**Workflow: Config Fields Validation**

1. Fetch sample data через MCP
2. Извлечь набор полей и типов
3. Сравнить с полями в pipeline config (`primary_keys`, `sort_by`, DQ `rules[].field`)
4. При расхождении → finding `CFG-DRIFT-*`

### Open Targets — reference для composite config

| Сценарий | Инструмент | Параметры | Результат |
|----------|------------|-----------|-----------|
| Available fields | `Open Targets:get_open_targets_graphql_schema` | — | Поля для composite merge/column_order |
| Join key validation | `Open Targets:search_entities` | `query_strings=["EGFR"]` | Проверка join keys (ensemblId mapping) |

---

## Platform Tools

| Инструмент | Когда использовать | Пример |
|------------|-------------------|--------|
| `web_search` | Документация YAML schema validation, JSON Schema | `web_search("yaml json schema validation python")` |

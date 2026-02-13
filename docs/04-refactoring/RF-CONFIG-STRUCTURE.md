# RF-CONFIG-STRUCTURE: Рефакторинг структуры конфигурационных файлов

**Версия:** 1.0.0
**Дата:** 2026-02-13
**Статус:** DRAFT
**Автор:** AI Agent (py-plan-bot)
**Связано с:** ADR-027, ADR-028, ADR-029, RULES.md §2.4, §3.1

---

## 1. Мотивация

Текущая система конфигов BioETL исторически росла органически: сначала всё было inline
в pipeline configs, затем DQ и filter были экстернализованы (ADR-027, ADR-028), добавлены
convention-based defaults (ADR-029), composite pipelines, data_schema. В результате:

- **126 YAML-файлов** в 7 подкаталогах `configs/`
- **3 стиля** написания pipeline configs (minimal, explicit full, hybrid) без чёткого гайда когда какой
- **Дублирование** primary_keys в 4 местах (top-level, sink.silver.primary_key, sort_by.columns × 2)
- **Непоследовательное именование** полей (thresholds vs dq_thresholds, field_validations vs entity_field_validations)
- **Устаревшие entity names** в sources configs (document вместо publication)
- **Разнородная структура** source configs (timeout_sec vs timeout, разный формат rate_limit)
- **Неочевидный merge-порядок** — чтобы понять итоговый конфиг, нужно загрузить 4+ файла

---

## 2. Цели рефакторинга

| # | Цель | Метрика |
|---|------|---------|
| G1 | **Единый стиль** pipeline configs | 100% configs в convention-based minimal стиле |
| G2 | **Устранение дублирования** | 0 дублированных primary_keys/sort_by/paths |
| G3 | **Унифицированное именование** полей | Единая терминология DQ/filter через все уровни |
| G4 | **Simplified source configs** | Стандартная схема для всех 7 провайдеров |
| G5 | **Актуальные entity names** | Все naming_exceptions применены |
| G6 | **Прозрачный merge** | Команда `bioetl config show <pipeline>` показывает resolved config |
| G7 | **Сокращение LOC** | ≥30% меньше строк в configs/ без потери информации |

---

## 3. Анализ текущего состояния

### 3.1 Структура `configs/`

```
configs/                              # 126 файлов
├── sources/          (7 файлов)      # Конфиги провайдеров API
├── pipelines/        (32 файла)      # Pipeline конфиги (включая _base.yaml, schemas)
│   ├── _base.yaml                    # 492 LOC — master template
│   ├── _schema.json                  # JSON Schema валидация
│   ├── _composite_schema.json
│   ├── chembl/       (14 entities)
│   ├── composite/    (5 entities)
│   └── {6 других провайдеров}
├── filter/           (41 файл)       # Фильтры: defaults → providers → entities
│   ├── _defaults.yaml
│   ├── providers/    (7 провайдеров)
│   └── entities/     (10+ директорий)
├── dq/               (39 файлов)     # DQ rules: defaults → providers → entities
│   ├── _defaults.yaml
│   ├── providers/    (7 провайдеров)
│   └── entities/     (10+ директорий)
├── data_schema/      (25 файлов)     # Схемы колонок для Gold output
│   ├── examples/
│   └── {провайдеры}
├── composite/                        # Field groups для composite pipelines
│   └── field_groups/
└── naming_exceptions.yaml            # Маппинг API names → canonical names
```

### 3.2 Обнаруженные проблемы

#### P1: Дублирование primary_keys (MEDIUM, ~100 точек)

```yaml
# Одна и та же информация в 4 местах:
primary_keys: ["activity_id"]           # 1) Top-level
sink:
  silver:
    primary_key: ["activity_id"]        # 2) Дубль
    sort_by:
      columns: ["activity_id"]          # 3) Дубль
  gold:
    sort_by:
      columns: ["activity_id"]          # 4) Дубль
```

**Факт:** Config loader уже умеет auto-propagate (ADR-029), но ~50% конфигов
всё ещё дублируют эти значения явно.

#### P2: Два стиля — convention vs explicit (MEDIUM)

**Minimal (chembl/activity.yaml):** 85 строк, convention-based
```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
# Пути НЕ указаны — auto-computed
```

**Explicit (chembl/molecule.yaml):** 117 строк, explicit paths
```yaml
pipeline_name: chembl_molecule
source_file: ../../sources/chembl.yaml          # Explicit — дубль конвенции
dq_config_file: ../../dq/entities/chembl/molecule.yaml  # Explicit — дубль конвенции
sink:
  bronze:
    path: "data/output/bronze/chembl/molecule"  # Explicit — дубль конвенции
  silver:
    path: "data/output/silver/chembl/molecule"  # Explicit — дубль конвенции
    csv_export:
      path: "data/output/silver/chembl/molecule"  # Explicit — дубль конвенции
```

**Проблема:** Разработчик не знает какой стиль выбрать. _base.yaml описывает 3 стиля
но нет enforcement. Explicit файлы на 40% длиннее без дополнительной информации.

#### P3: Непоследовательные имена полей DQ (MEDIUM)

| Уровень | Ключ | Содержимое |
|---------|------|------------|
| `dq/_defaults.yaml` | `common_field_validations` | Валидации для всех entities |
| `dq/providers/*.yaml` | `provider_field_validations` | Валидации для провайдера |
| `dq/entities/*/*.yaml` | `entity_field_validations` | Валидации для entity |
| `pipelines/*/*.yaml` | `dq_rules.field_validations` | Inline overrides |

4 разных ключа для семантически одинаковых списков. Код в `dq_config_loader.py`
знает как их сливать, но для читателя YAML это не очевидно.

#### P4: Source configs — разнородная структура (MEDIUM)

| Поле | ChEMBL | Semantic Scholar | PubMed |
|------|--------|------------------|--------|
| `rate_limit.requests_per_second` | `3` | `0.1` | `3.0` |
| `rate_limit.with_api_key` | ❌ | `{rps: 1.0, burst: 5}` | ❌ |
| `rate_limit.window` | ❌ | `300` | ❌ |
| `health_check.timeout` | `5` | `30` | `5` |
| `health_check.params` | ❌ | `{query: test, ...}` | ❌ |
| `health_check.skip_on_429` | ❌ | `true` | ❌ |
| `client.retry_base_delay` | ❌ | `30.0` | ❌ |
| `batch_size` (source level) | `10` | `50` | `100` |
| `batch_size` (provider_config level) | `10` | `50` | ❌ |

**Проблема:** `batch_size` дублируется на 2 уровнях. `with_api_key` — нестандартный
nested key, есть только у Semantic Scholar. Таймауты указаны в разных форматах.

#### P5: Устаревшие entity names в sources (MEDIUM)

```yaml
# configs/sources/chembl.yaml
entities:
  - document              # ❌ Должно быть: publication (ADR-024)
  - document_similarity   # ❌ Должно быть: publication_similarity
  - document_term         # ❌ Должно быть: publication_term
```

Все pipeline/filter/dq конфиги уже используют `publication`, но source config не обновлён.

#### P6: _base.yaml слишком длинный (LOW)

492 строки, из них ~60% — комментарии-документация. Полезная нагрузка ≈ 200 строк.
Документация в _base.yaml дублирует ADR-029 и RULES.md. При этом конфиг трудно
читать из-за объёма комментариев.

#### P7: `data_schema/` — неопределённая роль (LOW)

Большинство файлов пустые (`column_groups: []`). Только composite field_groups
реально используются. Пустые YAML-файлы создают ложное впечатление что они нужны.

#### P8: Дублирование batch_size между filter и sources (LOW)

```yaml
# configs/filter/providers/chembl.yaml
input_filter:
  batch_size: 20

# configs/sources/chembl.yaml
source:
  batch_size: 10
  provider_config:
    batch_size: 10
```

Три места определения batch_size для одного провайдера. Какой из них "правильный" —
зависит от контекста (API batch vs filter batch), но это нигде не документировано.

#### P9: Extraction params — нестандартный feature (LOW)

`extraction_params` существует только в `filter/entities/chembl/activity.yaml`.
Нет ни в `_defaults.yaml`, ни в документации иерархии. Потенциально полезен для
UniProt, PubMed, но не обобщён.

#### P10: DQ thresholds — разные ключи (MEDIUM)

```yaml
# dq/_defaults.yaml — стандартный формат
thresholds:
  soft_fail: 0.05
  hard_fail: 0.20

# sources/uniprot.yaml — нестандартный формат
dq_thresholds:        # ❌ Другой ключ!
  soft_fail: 0.30
  hard_fail: 0.80
```

---

## 4. Целевая структура

### 4.1 Новая структура `configs/`

```
configs/
├── _schema/                          # JSON Schemas (из pipelines/)
│   ├── pipeline.json
│   └── composite.json
├── sources/                          # БЕЗ ИЗМЕНЕНИЙ (кроме унификации полей)
│   ├── chembl.yaml
│   └── ...
├── pipelines/                        # УПРОЩЕНЫ — только convention-based minimal
│   ├── _base.yaml                    # УПРОЩЁН — убраны дублирующие комментарии
│   ├── chembl/
│   │   ├── activity.yaml             # ~30 строк вместо 85
│   │   └── ...
│   └── composite/
│       └── ...
├── quality/                          # ПЕРЕИМЕНОВАНО из dq/ — более понятное имя
│   ├── _defaults.yaml                # Унифицированное именование полей
│   ├── providers/
│   └── entities/
├── filters/                          # ПЕРЕИМЕНОВАНО из filter/ (множ. число)
│   ├── _defaults.yaml
│   ├── providers/
│   └── entities/
├── schemas/                          # ПЕРЕИМЕНОВАНО из data_schema/
│   ├── chembl/
│   └── composite/
│       └── field_groups/             # Перенесено из composite/field_groups/
└── naming_exceptions.yaml
```

### 4.2 Ключевые изменения

#### 4.2.1 Pipeline configs — только convention-based minimal

**До (chembl/molecule.yaml — 117 строк):**
```yaml
pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
version: "1.2.0"
description: "Extract molecules/compounds from ChEMBL API"
primary_keys: ["molecule_id"]
silver_table: "chembl_molecule"
gold_table: "chembl_molecule"
source_file: ../../sources/chembl.yaml
dq_config_file: ../../dq/entities/chembl/molecule.yaml
data_schema_file: ../../data_schema/chembl/molecule.yaml
sink:
  bronze:
    path: "data/output/bronze/chembl/molecule"
  silver:
    path: "data/output/silver/chembl/molecule"
    primary_key: ["molecule_id"]
    partition_by: ["molecule_type"]
    sort_by:
      columns: ["molecule_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/molecule"
  gold:
    path: "data/output/gold/chembl/molecule"
    sort_by:
      columns: ["molecule_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/molecule"
dq_rules:
  field_validations: [...]
  cross_field_validations: [...]
```

**После (chembl/molecule.yaml — ~40 строк):**
```yaml
# ChEMBL Molecule Pipeline
# All paths, file refs, primary_key propagation auto-computed (ADR-029)
pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
version: "1.3.0"
description: "Extract molecules/compounds from ChEMBL API"

primary_keys: ["molecule_id"]
silver_table: chembl_molecule
gold_table: chembl_molecule

# Entity-specific overrides only
sink:
  silver:
    partition_by: ["molecule_type"]

# DQ overrides on top of quality/entities/chembl/molecule.yaml
dq_overrides:
  field_validations:
    - field: molecule_type
      type: enum
      allowed: [Small molecule, Protein, Antibody, Oligosaccharide, Oligonucleotide, Cell, Enzyme, Unknown]
      nullable: true
    - field: canonical_smiles
      type: custom
      validator: smiles_validator
      nullable: true
    - field: full_mwt
      type: range
      min: 10
      max: 10000
      nullable: true
      error_message: "Molecular weight must be between 10 and 10000 Da"
  cross_field_validations:
    - name: structure_completeness
      fields: [canonical_smiles, standard_inchi, standard_inchi_key]
      condition: any_present
```

**Удалено:**
- `source_file`, `dq_config_file`, `data_schema_file` — convention auto-computes
- `sink.*.path` — convention auto-computes
- `sink.silver.primary_key` — auto-propagated from `primary_keys`
- `sink.*.sort_by.columns` — auto-propagated from `primary_keys`
- `sink.*.csv_export.path` — auto-computed from sink path

**Переименовано:**
- `dq_rules` → `dq_overrides` (чётко показывает что это overrides, а не полный набор)

#### 4.2.2 Унификация именования DQ полей

**До:** 4 разных ключа в зависимости от уровня иерархии

**После:** Единый ключ `field_validations` на ВСЕХ уровнях

| Уровень | До | После |
|---------|-----|-------|
| Defaults | `common_field_validations` | `field_validations` |
| Provider | `provider_field_validations` | `field_validations` |
| Entity | `entity_field_validations` | `field_validations` |
| Pipeline | `dq_rules.field_validations` | `dq_overrides.field_validations` |

Аналогично для `cross_field_validations` и `conditional_validations`.

Семантика merge остаётся той же: concatenate + deduplicate by name/field.
Уровень определяется расположением файла, а не именем ключа.

#### 4.2.3 Source configs — нормализация

**Стандартная структура для ВСЕХ провайдеров:**

```yaml
# configs/sources/{provider}.yaml
version: "1.0.0"

api:
  base_url: https://...
  auth_type: public | email | api_key
  api_key: ${ENV_VAR}           # Только если auth_type: api_key

client:
  timeout_sec: 60.0
  max_retries: 3
  retry_base_delay: 2.0        # Единый стандарт, не только у S2
  retry_max_delay: 120.0

batch:
  api_batch_size: 10            # Размер batch для API запросов
  page_size: 100                # Размер страницы пагинации
  max_url_length: 2000          # Только для GET-based APIs

rate_limit:
  default:                      # Без API key / базовые лимиты
    requests_per_second: 3
    burst: 10
  authenticated:                # С API key (опционально)
    requests_per_second: 10
    burst: 50

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 300

health_check:
  endpoint: /status
  method: GET
  timeout_sec: 5               # Единый суффикс _sec для таймаутов
  params: {}                   # Опционально
  skip_on_429: false           # Опционально

retry:
  use_retry_after: false

entities:
  - activity
  - publication                 # ✅ Canonical names (ADR-024)
```

**Ключевые нормализации:**
- `source.provider_config.*` → вынесены на верхний уровень (`api`, `client`, `batch`)
- `batch_size` (дубль) → единственный `batch.api_batch_size`
- `rate_limit.with_api_key` → `rate_limit.authenticated` (стандартное имя)
- `timeout` → `timeout_sec` везде (единый суффикс)
- `document` → `publication` в entities (ADR-024)

#### 4.2.4 _base.yaml — slim version

**До:** 492 строки (60% комментарии)
**После:** ~150 строк (только defaults + краткие inline комментарии)

Документация вынесена в `docs/04-refactoring/CONFIG-GUIDE.md` вместо дублирования
в YAML-файле. _base.yaml содержит только значения defaults.

#### 4.2.5 `data_schema/` → `schemas/` + cleanup

- Переименование каталога: `data_schema/` → `schemas/`
- Удаление пустых файлов (`column_groups: []`) — loader обрабатывает отсутствие файла
- Перенос `composite/field_groups/` → `schemas/composite/field_groups/`
- Удаление `examples/` (устаревшие примеры)

#### 4.2.6 DQ thresholds — единый формат

Удалить `dq_thresholds` из source configs. Thresholds определяются ТОЛЬКО в
`quality/` иерархии (defaults → providers → entities → pipeline overrides).

---

## 5. План реализации

### Phase 1: Подготовка (non-breaking)

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 1.1 | Исправить entity names в sources (document→publication) | `configs/sources/chembl.yaml` | LOW |
| 1.2 | Добавить обратную совместимость в config loaders для новых ключей | `infrastructure/config/*.py` | MEDIUM |
| 1.3 | Написать migration-тесты: load old format → verify same domain objects | `tests/` | LOW |

### Phase 2: Нормализация source configs

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 2.1 | Определить Pydantic schema `SourceConfigV2` | `infrastructure/schemas/source_config.py` | LOW |
| 2.2 | Мигрировать 7 source configs на новую структуру | `configs/sources/*.yaml` | MEDIUM |
| 2.3 | Обновить `_config_helpers.py` под новую структуру | `composition/providers/_config_helpers.py` | MEDIUM |
| 2.4 | Тесты: все адаптеры создаются корректно из нового формата | `tests/` | LOW |

### Phase 3: Унификация DQ naming

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 3.1 | Добавить alias-поддержку в `dq_config_loader.py` (old keys → new keys) | `infrastructure/config/dq_config_loader.py` | MEDIUM |
| 3.2 | Мигрировать `dq/_defaults.yaml` → `quality/_defaults.yaml` | `configs/quality/` | MEDIUM |
| 3.3 | Мигрировать все DQ provider/entity configs на единые ключи | `configs/quality/**/*.yaml` | MEDIUM |
| 3.4 | Переименовать `dq_rules` → `dq_overrides` в pipeline configs | `configs/pipelines/**/*.yaml` | MEDIUM |
| 3.5 | Удалить `dq_thresholds` из source configs | `configs/sources/*.yaml` | LOW |

### Phase 4: Упрощение pipeline configs

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 4.1 | Удалить дублированные `source_file`, `dq_config_file`, `data_schema_file` | `configs/pipelines/**/*.yaml` | LOW |
| 4.2 | Удалить дублированные `sink.*.path`, `primary_key`, `sort_by.columns` | `configs/pipelines/**/*.yaml` | MEDIUM |
| 4.3 | Удалить дублированные `csv_export.path` | `configs/pipelines/**/*.yaml` | LOW |
| 4.4 | Slim down `_base.yaml` — убрать документацию в отдельный файл | `configs/pipelines/_base.yaml` | LOW |
| 4.5 | Перенести JSON schemas: `_schema.json` → `configs/_schema/` | `configs/` | LOW |

### Phase 5: Реорганизация каталогов

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 5.1 | `filter/` → `filters/` (plural consistency) | `configs/filters/` | MEDIUM |
| 5.2 | `dq/` → `quality/` | `configs/quality/` | MEDIUM |
| 5.3 | `data_schema/` → `schemas/` + удаление пустых файлов | `configs/schemas/` | MEDIUM |
| 5.4 | `composite/field_groups/` → `schemas/composite/field_groups/` | `configs/schemas/` | LOW |
| 5.5 | Обновить все config loaders для новых путей с fallback на старые | `infrastructure/config/*.py`, `infrastructure/config_loader.py` | HIGH |
| 5.6 | Обновить README файлы | `configs/quality/README.md`, `configs/filters/README.md` | LOW |

### Phase 6: Финализация

| # | Задача | Файлы | Risk |
|---|--------|-------|------|
| 6.1 | Удалить fallback-код для старых путей/ключей | `infrastructure/config/*.py` | LOW |
| 6.2 | Обновить ADR-027, ADR-028, ADR-029 с новыми путями | `docs/02-architecture/decisions/` | LOW |
| 6.3 | Обновить `CONFIG-GUIDE.md` | `docs/04-refactoring/` | LOW |
| 6.4 | Финальный прогон тестов + architecture tests | - | LOW |
| 6.5 | CLI команда `bioetl config show <pipeline>` для resolved config | `interfaces/cli/` | MEDIUM |

---

## 6. Совместимость

### 6.1 Breaking changes

| Изменение | Кто затронут | Mitigation |
|-----------|-------------|------------|
| Переименование каталогов | Config loaders | Fallback на старые пути (Phase 5.5) |
| Новые ключи в DQ configs | DQ config loader | Alias-поддержка старых ключей (Phase 3.1) |
| Новая структура source configs | Adapter factories | Pydantic V2 с alias support (Phase 2.1) |
| `dq_rules` → `dq_overrides` | Pipeline configs | Alias в Pydantic schema |

### 6.2 Стратегия миграции

1. **Phase 1-3:** Добавить поддержку ОБОИХ форматов (old + new) в loaders
2. **Phase 4-5:** Мигрировать YAML файлы на новый формат
3. **Phase 6:** Удалить поддержку старого формата + deprecation warnings

### 6.3 Rollback plan

Каждая фаза — отдельный коммит. При проблемах — revert конкретной фазы.

---

## 7. Метрики успеха

| Метрика | До | После | Цель |
|---------|-----|-------|------|
| Суммарный LOC в `configs/` | ~4500 | ~3000 | -30% |
| Максимальный LOC pipeline config | 117 (molecule) | ~50 | -60% |
| Дублированных primary_keys | ~50 пар | 0 | 0 |
| Разных ключей для DQ validations | 4 | 1 | 1 |
| Стилей pipeline configs | 3 | 1 | 1 |
| Pydantic warnings при загрузке | Неизвестно | 0 | 0 |
| Тесты проходят | ✅ | ✅ | ✅ |

---

## 8. Риски

| Риск | Вероятность | Impact | Mitigation |
|------|------------|--------|------------|
| Сломанные pipeline runs после миграции | MEDIUM | HIGH | Migration-тесты (Phase 1.3), dual-format support |
| Merge конфликты с другими ветками | LOW | MEDIUM | Мигрировать YAML в отдельных коммитах по провайдерам |
| Composite pipeline configs сложнее чем ожидалось | LOW | MEDIUM | Composite configs минимально затрагиваются — их структура уже хорошая |
| Config loader regression | MEDIUM | HIGH | Architecture tests + integration tests |

---

## 9. Что НЕ входит в scope

- Изменение доменной модели (`domain/config/*.py`) — только если необходимо для поддержки новых ключей
- Рефакторинг самих config loaders (архитектура) — только адаптация к новым путям/ключам
- Новая CLI команда `config show` — опционально, Phase 6.5
- Изменение merge-семантики (concatenate vs override) — текущая семантика сохраняется
- Рефакторинг composite pipeline config format — уже хорошо структурирован

---

## 10. Зависимости

- **ADR-027** (DQ externalization) — обновить с новыми путями
- **ADR-028** (Filter externalization) — обновить с новыми путями
- **ADR-029** (Convention-based paths) — обновить с новыми каталогами
- **RULES.md** — обновить ссылки на configs/
- **CI/CD** — если есть hardcoded пути к configs/ в pipeline scripts

---

## Appendix A: Полный перечень переименований каталогов

| Старый путь | Новый путь |
|-------------|-----------|
| `configs/dq/` | `configs/quality/` |
| `configs/filter/` | `configs/filters/` |
| `configs/data_schema/` | `configs/schemas/` |
| `configs/composite/field_groups/` | `configs/schemas/composite/field_groups/` |
| `configs/pipelines/_schema.json` | `configs/_schema/pipeline.json` |
| `configs/pipelines/_composite_schema.json` | `configs/_schema/composite.json` |

## Appendix B: Полный перечень переименований ключей

| Контекст | Старый ключ | Новый ключ |
|----------|-------------|-----------|
| DQ defaults | `common_field_validations` | `field_validations` |
| DQ defaults | `common_cross_field_validations` | `cross_field_validations` |
| DQ providers | `provider_field_validations` | `field_validations` |
| DQ entities | `entity_field_validations` | `field_validations` |
| DQ entities | `entity_cross_field_validations` | `cross_field_validations` |
| DQ entities | `entity_conditional_validations` | `conditional_validations` |
| Pipeline | `dq_rules` | `dq_overrides` |
| Source | `source.provider_config` | `api` + `client` + `batch` (flattened) |
| Source | `rate_limit.with_api_key` | `rate_limit.authenticated` |
| Source | `timeout` (health_check) | `timeout_sec` |
| Source | `source.batch_size` | `batch.api_batch_size` |
| Source | `dq_thresholds` | **удалить** (используется quality/ hierarchy) |

## Appendix C: Пример resolved config output

```
$ bioetl config show chembl_activity

Pipeline: chembl_activity (v1.3.0)
Provider: chembl | Entity: activity

Sources:
  _base.yaml → pipelines/chembl/activity.yaml
  quality/_defaults.yaml → quality/providers/chembl.yaml → quality/entities/chembl/activity.yaml
  filters/_defaults.yaml → filters/providers/chembl.yaml → filters/entities/chembl/activity.yaml

Resolved Config:
  primary_keys: [activity_id]
  sink.silver.path: data/output/silver/chembl/activity
  sink.silver.primary_key: [activity_id]  (auto-propagated)
  sink.silver.sort_by: [activity_id] ASC  (auto-propagated)
  ...

DQ Rules (merged):
  thresholds: soft=0.05, hard=0.15 (from quality/providers/chembl.yaml)
  field_validations: 8 rules (2 common + 3 provider + 1 entity + 2 pipeline)
  cross_field_validations: 2 rules
  conditional_validations: 2 rules

Filters:
  input_filter: disabled
  silver_filters: 5 required_fields, 2 column filters, 1 range filter
  gold_filters: 3 required_fields, 2 column filters
  extraction_params: 7 params (server-side)
```

______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Политика файлов и директорий

*Синхронизировано с RULES.md v6.1.2 | Последнее обновление: 2026-04-12*

______________________________________________________________________

## Обзор

Данный документ описывает политику организации файлов и директорий проекта BioETL,
включая иерархию конфигураций и структуру выходных данных. Правила именования
классов и переменных вынесены в [02-naming-policy.md](02-naming-policy.md).

______________________________________________________________________

## 0. Политика корня репозитория

- Root-level tracked файлы MUST соответствовать `.github/root-allowlist.txt`.
- Root-level tracked markdown и txt артефакты MUST быть ограничены canonical
  root entrypoints. Операционные quick-reference материалы SHOULD жить в
  `docs/05-operations/`, а одноразовые status/recovery/final-summary артефакты
  MUST архивироваться под `docs/99-archive/`.
- Root-level tracked директории MUST ограничиваться approved runtime/tooling and
  project surfaces: `.ai`, `.aiassistant`, `ai`, `.codex`,
  `.cursor`, `.gemini`, `.github`, `.idea`, `.jules`, `.junie`, `.sonarlint`,
  `.vibe`, `.vscode`, `assets`, `configs`, `data`, `docs`, `grafana`,
  `reports`, `scripts`, `src`, and `tests`.
- Служебные локальные деревья (`.worktrees/`, `.rollback/`) MUST NOT попадать в git-index.
- Shared repo tooling surfaces such as `.codex/`, `.gemini/`, `.vibe/`,
  `.vscode/`, and `.cursor/` MAY оставаться tracked только если они
  поддерживаются как проектные runtime/editor integrations.
- `.idea/` MAY содержать curated shared project metadata (например,
  run configurations, scopes, inspections, словарь), но local/plugin state
  files such as `workspace.xml`, `shelf/`, `dataSources*/`, `.ai/`,
  `AICommit.xml`, `claudeCodeTabState.xml`, `codex.xml`,
  `copilot.data.migration*.xml`, `csv-editor.xml`, `git_toolbox_prj.xml`,
  `junie.xml`, `sonarlint.xml`, and `webResources.xml` MUST оставаться
  untracked.
- Локальные tooling-каталоги без статуса shared repo surface (например,
  `.sonarlint/`, `.trae/`, `.windsurf/`) MAY существовать в рабочем дереве,
  но MUST оставаться untracked и игнорироваться `.gitignore`.
- Generated/runtime root trees such as `node_modules/`, `output/`, `test-output/`,
  `logs/`, `MagicMock/`, and local package trees like `.python-user/` MUST NOT
  попадать в git-index.

Root allowlist интерпретируется как policy surface, а не как временный склад.
Если новый root-level файл существует только для инцидента, ручной проверки или
финального статуса волны, он не должен закрепляться в корне.

`.codex_tmp/` is a local scratch/cache surface and MUST remain untracked.
`.vibe/` may remain tracked only for curated project-local Mistral Vibe
configuration such as `.vibe/config.toml`; credentials, runtime state, and
generated local package/output trees are excluded from this exception.

Проверка:

```bash
python3 scripts/engineering/repo/audit_root_cleanliness.py
python3 scripts/engineering/diagnostics/audit_structure.py --path .
```

Дополнительные правила маршрутизации:

- active deployment / verification / runbook docs → `docs/05-operations/`
- repo-only evidence and historical status artifacts → `docs/99-archive/`
- generated working outputs → `reports/`
- generated helper exports and merged snapshots MUST NOT live under `src/`;
  they belong in `reports/` or another non-source artifact surface

### 0.1. Структурный каталог и retention-sensitive зоны

Machine-readable каталог для structure hygiene хранится в
`configs/quality/repo_structure_catalog.yaml`.

Он фиксирует:

- допустимую D-серию `docs/D-*.md` как `repo-only sync notes` с каноническими
  successor pages;
- разрешённый живой состав `docs/plans/**` и правило `max_active_backlog = 1`;
- допустимые sidecar roots под `src/`: `src/bioetl`, `src/tools`,
  `src/memory`;
- approved docs-resident code zones under `docs/00-project/ai/agents/**` and
  `docs/plugins/link_checker/**`;
- tolerated local-only hidden root trees such as `.agent-work/`,
  `.agentbridge/`, `.cache/`, `.coverage-sharded/`, `.scannerwork/`,
  `.venv-docs/`, `.venv-win/`, and `.venv-win-corrupt/`;
- blocked cleanup zones, которые не должны попадать под broad cleanup.

`scripts/engineering/repo/audit_root_cleanliness.py` MUST использовать этот
каталог как источник правды для structure drift beyond root allowlist.

### 0.2. Legacy flat docs (`docs/D-*.md`)

- `docs/D-*.md` MUST оставаться `repo-only` и MUST NOT публиковаться в MkDocs.
- Каждый такой файл MUST иметь явный `canonical_successor` в
  `configs/quality/repo_structure_catalog.yaml`.
- Новые `docs/D-*.md` MUST NOT добавляться без явного обновления каталога и
  review structure governance.
- D-серия не является normative surface; при конфликте приоритет всегда у
  `docs/00-05/**`.

### 0.3. Plans surface (`docs/plans/**`)

- `docs/plans/**` является repo-only planning surface.
- Только один файл MAY иметь lifecycle `active_backlog`; остальные файлы в
  этом каталоге должны быть `supporting_context` или должны переезжать в
  archive/report surfaces.
- Каждый tracked plan file MUST быть зарегистрирован в
  `configs/quality/repo_structure_catalog.yaml`.
- Закрытые или purely historical plan artifacts SHOULD переезжать в
  `docs/99-archive/**` или закрепляться в evidence/report surfaces, а не
  накапливаться как competing active docs.

### 0.4. Sidecar code under `src/`

- `src/bioetl/` остаётся canonical runtime tree.
- `src/tools/` разрешён как approved sidecar tooling surface для project
  utilities, которые могут импортировать `bioetl`, но не являются primary
  contributor entrypoint.
- `src/memory/` разрешён как approved sidecar memory subsystem с собственной
  policy/schema/tooling поверхностью.
- Новые top-level пакеты под `src/` вне этих трёх roots MUST FAIL structure
  governance until they are explicitly ratified.

### 0.4.1. Shared test support under `tests/`

- Shared test helper modules SHOULD жить под `tests/testing_support/`.
- Такие helper-модули не являются runtime surface и MUST использоваться только
  для test-only support code.
- Новые root-level test support directories не допускаются; тестовая shared
  support code должна оставаться внутри уже разрешённого дерева `tests/`.

### 0.4.2. Approved docs-resident code zones

- Python code under `docs/**` остаётся запрещённым по умолчанию.
- Исключения MUST быть явно зарегистрированы в
  `configs/quality/repo_structure_catalog.yaml`.
- Текущие ratified zones:
  - `docs/00-project/ai/agents/policy/`
  - `docs/00-project/ai/agents/scripts/`
  - `docs/plugins/link_checker/`
- Эти зоны считаются repo-only documentation/governance tooling surfaces и не
  дают blanket permission на размещение нового Python-кода в других частях
  `docs/**`.

### 0.4.3. Tolerated local hidden root trees

- Hidden root directories, зарегистрированные как
  `local_tolerated_root_dirs` в structure catalog, MAY существовать в рабочем
  дереве как untracked local runtime/editor state.
- Такие каталоги не считаются approved tracked project surfaces и MUST NOT
  использоваться как justification для новых tracked roots.

### 0.5. Retention boundary

Следующие зоны являются blocked cleanup zones и MUST NOT рассматриваться как
обычный structural мусор:

- `docs/99-archive/**` — traceability/history archive
- `tests/fixtures/**`, `tests/fixtures/vcr/**` — reproducibility fixtures
- `docs/reports/**` — curated repo-only reports
- `reports/**` — generated/working outputs с отдельной cleanup policy
- `data/**` — runtime/control-plane/data retention surface

Для этих зон допустим только bounded cleanup по специализированным процедурам.
Blanket cleanup команды и broad deletion waves для них запрещены.
GitHub cleanup proposals for these zones MUST use
`.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml` or provide the same
evidence pack required by
`docs/05-operations/runbooks/retention-sensitive-cleanup.md`.

______________________________________________________________________

## 1. Структура Конфигураций Pipeline

### 1.1. Иерархия файлов

```text
configs/
├── _schema/
│   ├── pipeline.json
│   └── composite.json
├── base/
│   ├── pipeline.yaml
│   └── quality.yaml
├── providers/
│   └── <provider>.yaml
├── entities/
│   └── <provider>/<entity>.yaml
├── composites/
│   ├── <entity>.yaml
│   └── field_groups/*.yaml
└── enums/
```

### 1.2. Цепочка наследования

```text
configs/base/*.yaml (базовые значения) → configs/entities/<provider>/<entity>.yaml
```

`configs/providers/<provider>.yaml` хранит параметры источника и ограничения клиента.

### 1.3. Обязательные поля entity config

Каждый entity config (`<provider>/<entity>.yaml`) **MUST** содержать:

| Поле                    | Описание                                       | Пример            |
| ----------------------- | ---------------------------------------------- | ----------------- |
| `pipeline_name`         | Уникальный идентификатор `{provider}_{entity}` | `chembl_activity` |
| `provider`              | Имя провайдера                                 | `chembl`          |
| `entity_type`           | Тип сущности                                   | `activity`        |
| `version`               | Семантическая версия                           | `"1.1.0"`         |
| `business_primary_keys` | Первичный ключ                                 | `["activity_id"]` |
| `silver_table`          | Имя Silver-таблицы                             | `chembl_activity` |
| `gold_table`            | Имя Gold-таблицы                               | `chembl_activity` |
| `sink`                  | Пути к слоям с `sort-by`                       | См. ниже          |

### 1.4. Валидация конфигураций

Все entity configs валидируются через `configs/_schema/pipeline.json`:

```bash
# Pre-commit hook автоматически проверяет конфиги
# Ручная валидация:
python -c "import json, yaml, jsonschema; \
  schema = json.load(open('configs/_schema/pipeline.json')); \
  config = yaml.safe_load(open('configs/entities/chembl/activity.yaml')); \
  jsonschema.validate(config, schema)"
```

______________________________________________________________________

## 2. Иерархия путей для данных

### 2.1. Паттерн путей

Все выходные данные следуют иерархической структуре:

```
data/output/{layer}/{provider}/{entity}/
```

| Слой             | Паттерн пути                                  | Пример                                    |
| ---------------- | --------------------------------------------- | ----------------------------------------- |
| **Bronze**       | `data/output/bronze/{provider}/{entity}/`     | `data/output/bronze/chembl/activity/`     |
| **Silver**       | `data/output/silver/{provider}/{entity}/`     | `data/output/silver/chembl/activity/`     |
| **Gold**         | `data/output/gold/{provider}/{entity}/`       | `data/output/gold/chembl/activity/`       |
| **CSV (Silver)** | `data/output/csv/silver/{provider}/{entity}/` | `data/output/csv/silver/chembl/activity/` |
| **CSV (Gold)**   | `data/output/csv/gold/{provider}/{entity}/`   | `data/output/csv/gold/chembl/activity/`   |

### 2.2. Пример конфигурации sink

```yaml
sink:
  bronze:
    path: "data/output/bronze/chembl/activity"
  silver:
    path: "data/output/silver/chembl/activity"
    primary_key: ["activity-id"]
    partition_by: []
    sort_by:
      columns: ["activity-id"]
      ascending: true
    csv_export:
      path: "data/output/csv/silver/chembl/activity"
  gold:
    path: "data/output/gold/chembl/activity"
    sort_by:
      columns: ["activity-id"]
      ascending: true
    csv_export:
      path: "data/output/csv/gold/chembl/activity"
```

### 2.3. Обязательность sort-by (ADR-014)

**MUST**: Все entity configs должны содержать `sort-by` для Silver и Gold слоёв.

Это требование обеспечивает:

- Детерминизм выходных данных
- Воспроизводимость при повторных запусках
- Стабильность diff-сравнений

См. [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md).

### 2.4. Допустимые категории файлов в `data/`

`data/` разделяется на категории с явной политикой включения в релизный контур:

| Категория          | Паттерн                                  | В релизе | Размерный лимит       | Назначение                                       |
| ------------------ | ---------------------------------------- | -------- | --------------------- | ------------------------------------------------ |
| Input fixtures     | `data/input/**/*.csv`                    | ✅ Да    | 30 MiB на файл        | Локальные входные наборы для ETL и отладки       |
| Reference fixtures | `data/input/reference/**/*.csv`          | ✅ Да    | 5 MiB на файл         | Небольшие справочники и классификаторы           |
| Test fixtures      | `data/fixtures/**/*.{csv,json,jsonl}`    | ✅ Да    | 10 MiB на файл        | Фикстуры для unit/integration/e2e тестов         |
| Golden datasets    | `data/golden/**/*.{csv,json,jsonl}`      | ✅ Да    | 20 MiB на файл        | Эталонные выборки для регрессионной проверки     |
| Local artifacts    | `data/local/**`, `data/tmp/**`, `tmp/**` | ❌ Нет   | Без лимита (локально) | Временные/тяжёлые рабочие артефакты разработчика |

**MUST**:

- Временные и тяжёлые файлы (например, XLSX-дампы, ad-hoc выгрузки, профилировочные снимки) хранить только в `data/local/` или `tmp/`.
- `data/local/` и `tmp/` НЕ включать в релизный контур (игнорируются Git/CI).
- Перед релизом запускать allowlist-проверку:

```bash
uv run python -m scripts.ops.data check-data-dir
```

______________________________________________________________________

## 3. Соглашения об именовании

### 3.1. Pipeline идентификаторы

| Паттерн                         | Описание           | Пример                    |
| ------------------------------- | ------------------ | ------------------------- |
| `{provider}_{entity}`           | Стандартный формат | `chembl_activity`         |
| `{provider}_{entity}_{variant}` | С вариантом        | `chembl_publication_term` |

**НЕ используется**: `{entity}_{provider}` (например, `activity_chembl`)

### 3.2. Имена таблиц

Silver и Gold таблицы используют тот же паттерн:

```yaml
silver_table: "chembl_activity"
gold_table: "chembl_activity"
```

______________________________________________________________________

## 4. Файлы провайдеров

### 4.1. Структура

```
configs/providers/<provider>.yaml
```

Содержит настройки API провайдера:

- `base-url` — базовый URL API
- `rate-limit` — лимиты запросов
- `timeout` — таймауты
- `retry` — настройки повторов
- `circuit-breaker` — настройки Circuit Breaker

### 4.2. Связь с entity config

```yaml
provider: chembl
```

______________________________________________________________________

## 5. Политика очистки

| Слой   | Retention | Примечание                 |
| ------ | --------- | -------------------------- |
| Bronze | 90 дней   | Автоматическая архивация   |
| Silver | Постоянно | Delta Lake VACUUM (7 дней) |
| Gold   | Постоянно | Delta Lake VACUUM (7 дней) |

См. [RULES.md §2.1.1](../RULES.md) для деталей политики retention.

______________________________________________________________________

## 6. Миграция и обратная совместимость

### 6.1. История изменений

| Версия | Дата       | Изменение                                                             |
| ------ | ---------- | --------------------------------------------------------------------- |
| 2.0.0  | 2026-01-14 | Унификация `-defaults.yaml`, удаление `-base.yaml`                    |
| 2.0.0  | 2026-01-14 | Иерархические пути `{layer}/{provider}/{entity}`                      |
| 2.0.0  | 2026-01-14 | Обязательный `sort-by` во всех entity configs                         |
| 2.0.0  | 2026-01-14 | JSON Schema валидация через `-schema.json`                            |
| 2.1.0  | 2026-02-24 | Добавлена governance-политика категорий для `data/` и лимиты размеров |

### 6.2. Проверка соответствия

```bash
# Проверить все конфиги
make validate-configs

# Или вручную через pre-commit
pre-commit run validate-pipeline-configs --all-files
```

______________________________________________________________________

## Связанные документы

- [RULES.md](../RULES.md) — Конституция проекта
- [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-025: Pipeline Config Unification](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [04-extending-bioetl.md](04-extending-bioetl.md) — Добавление новых pipeline

______________________________________________________________________

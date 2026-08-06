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

*Синхронизировано с RULES.md v6.1.3 | Последнее обновление: 2026-05-21*

______________________________________________________________________

## Обзор

Данный документ описывает политику организации файлов и директорий проекта BioETL,
включая иерархию конфигураций и структуру выходных данных. Правила именования
классов и переменных вынесены в [02-naming-policy.md](02-naming-policy.md).

______________________________________________________________________

## 0. Политика корня репозитория

### 0.0. Target root model

Root allowlist является минимальной моделью корня, а не накопительным списком
удобных entrypoints. Новые root-level файлы допускаются только после
синхронного обновления `.github/root-allowlist.txt`, этой политики,
`configs/quality/root_hygiene_review_registry.yaml` и, если файл является
generated output, `configs/quality/generated_artifact_routing.yaml`.

| Категория | Допустимые поверхности | Enforcement | Exit rule |
| --- | --- | --- | --- |
| Mandatory root minimum | project identity, package manager, security, license, and docs-tool files with exact-root contracts | `.github/root-allowlist.txt` and root cleanliness audit | move under `docs/**`, `configs/**`, or `scripts/**` when exact-root contract is gone |
| Tool-required root files | exact filenames required by Git, packaging, npm, pre-commit, docs tooling, MCP workspace bootstrap, and review tooling | root allowlist plus owner lane when transitional | keep only while tool contract requires exact root filename |
| Human-facing root docs | `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `AGENTS.md`, `GEMINI.md`, and reviewed vendor guidance such as `best_practices.md` | canonical root text policy in `audit_root_cleanliness.py` | non-canonical notes move to `docs/**` or `docs/99-archive/**` |
| Allowed root directories | approved runtime, tooling, project, data, docs, report, source, and test trees listed below and in `configs/quality/repo_structure_catalog.yaml` | structure catalog and root governance docs check | new root directories require explicit structure governance |
| Forbidden root files/directories | tracked `.env*` except `.env.example`, generated diagnostics, root scratch scripts/tests, local cache/output directories, and ad-hoc root dumps | strict root audit and generated-artifact routing | delete, ignore as local-only where approved, or route retained evidence to `reports/**` |
| Temporary compatibility surfaces | reviewed non-script exact-root compatibility entrypoints only | `configs/quality/root_hygiene_review_registry.yaml` owner lanes | root `.sh`, `.ps1`, `.py`, and `.bat` compatibility exceptions are closed and MUST NOT be restored |

| Agent skills lockfile | `skills-lock.json` | root allowlist + `root_hygiene_review_registry.yaml` lane `root_tooling_transitions` | **MUST stay exact root** while skill installer / lock tooling emit the documented filename; do not rehome speculatively (RH5-06 / #7023 closed as retain) |

Docker helper dispositions are resolved as follows and MUST stay aligned with
`docs/05-operations/verification/docker-helper-root-relocation-audit.md`:

| Surface | Disposition | Owner path / target | Exit rule |
| --- | --- | --- | --- |
| `Dockerfile.bioetl` | MUST stay root | `Dockerfile.bioetl` | move only after Docker workflow build inputs and manual build commands are repointed or wrapped |
| `docker-compose.yml` | MUST stay root | `docker-compose.yml` | move only behind a root-compatible shim or after default `docker compose` flows are repointed |
| `docker-compose.monitoring.yml` | MUST stay root | `docker-compose.monitoring.yml` | move only after monitoring CI/docs references use a new path or shim |
| `docker-compose.neo4j.yml` | MUST stay root | `docker-compose.neo4j.yml` | move only after Neo4j helper commands and docs are repointed |
| `docker-compose.neo4j-audit.yml` | MUST stay root | `docker-compose.neo4j-audit.yml` | move only after audit launchers and docs are repointed |
| `docker-setup.ps1` | retired root script | `scripts/ops/docker-setup.ps1` | do not restore root filename; use the scripts-owned command-compatible helper |
| `docker-setup.sh` | retired root script | `scripts/ops/docker-setup.sh` | do not restore root filename; use the scripts-owned command-compatible helper |
| `docker-compose.alertmanager.yml` | moved to owned path | `scripts/ops/runtime/docker/compose/alertmanager.yml` | do not restore root filename without fresh owner review |
| `docker-compose.minio.yml` | moved to owned path | `scripts/ops/runtime/docker/compose/minio.yml` | do not restore root filename without fresh owner review |
| `docker-compose.redis.yml` | moved to owned path | `scripts/ops/runtime/docker/compose/redis.yml` | do not restore root filename without fresh owner review |
| `docker-compose.sonarqube.yml` | moved to owned path | `scripts/ops/runtime/docker/compose/sonarqube.yml` | do not restore root filename without fresh owner review |
| `docker-compose.codex.yml`, `Dockerfile.mcp-*` | retired | `.mcp.json` and `scripts/ai/mcp/**` | do not restore persistent stdio MCP containers |
| `Dockerfile.warp` | retired | none | do not restore Warp to default/full startup |
| `grafana-datasource.yml` | moved to owned path | `grafana/provisioning/datasources-local/grafana-datasource.yml` | do not restore root filename without fresh owner review |

- Root-level tracked файлы MUST соответствовать `.github/root-allowlist.txt`.
- Required root-level `docker-compose*.yml` files MAY оставаться tracked only
  when operator flows require the exact root filename. Optional adjunct helper
  stacks MUST live under owned paths such as
  `scripts/ops/runtime/docker/compose/**`; they MUST NOT переопределять ADR-010
  and MUST NOT трактоваться как обязательный runtime bootstrap path.
- Stable helper governance anchor:
  `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT`; machine-readable helper contracts live
  in `configs/quality/docker_helper_contracts.yaml`.
- Root `.mcp.json` is an exact-root workspace MCP entrypoint for compatible
  tools and MUST remain tracked at the repository root. It MUST be generated
  from `scripts/ai/codex/setup_mcp.py`, stay repo-relative/portable, and stay
  synchronized with `scripts/ai/.mcp.json`. Machine-local absolute MCP paths are
  allowed only in documented generated local runtime surfaces such as
  `~/.codex/config.toml`, local ignored editor/runtime mirrors, or the reviewed
  `.devin/mcp_config.json` runtime surface; see
  `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`.
- Root-level tracked markdown и txt артефакты MUST быть ограничены canonical
  root entrypoints. Операционные quick-reference материалы SHOULD жить в
  `docs/05-operations/`, а одноразовые status/recovery/final-summary артефакты
  MUST архивироваться под `docs/99-archive/`.
- Reconciled `2026-07` tracked root baseline uses three explicit dispositions:
  canonical project/tooling entrypoints retained at root, canonical
  runtime/governance entrypoints retained at root, and reviewed ADR-010
  adjunct helper files rehomed under owned operational paths when exact root
  filenames are no longer required.
- Former root Codex / WSL setup notes were converged into canonical
  `docs/05-operations/**` runbooks and archived under
  `docs/99-archive/root-status-artifacts/ai-runtime-setup/`; they are no
  longer approved root entrypoints.
- Vendor-documented repo-wide guidance files MAY remain at root only when the
  external review/runtime contract requires the exact root filename. Current
  reviewed example: `best_practices.md` for Qodo policy ingestion, with its
  retention rationale documented under `docs/00-project/governance/qodo/`.
- Root launcher/setup shims such as `.wsl_proxy_env.sh`, `codex.ps1`,
  `codex.bat`, `setup-codex-wsl.*`, `run-codex.ps1`, and
  `run-codex-wsl.ps1` are retired from the repository root and MUST NOT be
  restored without fresh owner review. Maintained launcher, setup, and proxy
  logic MUST live under `scripts/**`: Codex launch/setup under
  `scripts/ai/codex/**`, Windows operator launchers under `scripts/ops/**`, and
  the shared WSL proxy helper under `scripts/engineering/dev/bash/.wsl_proxy_env.sh`.
- Root Docker helper relocation decisions MUST reference
  `docs/05-operations/verification/docker-helper-root-relocation-audit.md`
  before any helper/file move is approved.
- Raw generated test inventories and dumps (for example `tests.txt`) MUST NOT
  оставаться tracked в корне. Retained diagnostics and auditable test outputs
  MUST route into approved `reports/**` or archive/report surfaces instead of a
  root-level txt dump.
- Root-level tracked директории MUST ограничиваться approved runtime/tooling and
  project surfaces: `.agents`, `.codex`, `.cursor`, `.devin`, `.gemini`, `.github`,
  `.junie`, `.vibe`, `.vscode`, `.zed`, `artifacts`, `assets`, `configs`, `data`,
  `docs`, `grafana`, `reports`, `scripts`, `src`, and `tests`.
- Canonical machine-readable root governance lives in `.github/root-allowlist.txt`,
  `configs/quality/repo_structure_catalog.yaml`,
  `configs/quality/root_hygiene_review_registry.yaml`, and
  `configs/quality/generated_artifact_routing.yaml`; prose docs in this section
  MUST stay aligned with those enforcement surfaces.
- Служебные локальные деревья (`.worktrees/`, `.rollback/`) MUST NOT попадать в git-index.
- Shared repo tooling surfaces such as `.agents/`, `.codex/`, `.gemini/`, `.junie/`,
  curated `.vibe/`,
  and curated shared editor metadata roots such as `.cursor/`, `.vscode/`, and
  `.zed/` MAY оставаться tracked только если они поддерживаются как
  проектные runtime/editor integrations.
- Editor/vendor/tooling roots such as `.ai/`, `.aiassistant/`, `ai/`,
  `.jules/`, `.sonarlint/`, `.windsurf/`, `.agent-work/`,
  `.agentbridge/`, `.benchmarks/`, `.cache/`, `.qodo/`,
  `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.hypothesis/`,
  `.import_linter_cache/`, `.venv/`, `node_modules/`, and `test-output/`
  MAY существовать в рабочем дереве, но MUST оставаться untracked и
  игнорироваться `.gitignore`, если не были явно promoted через structure
  governance.
- `.vscode/`, `.cursor/`, and `.zed/` MAY содержать curated shared project
  metadata (например, run configurations, scopes, inspections, словарь), но по
  умолчанию рассматриваются как local/editor state surfaces и MUST оставаться
  untracked, если не зарегистрированы как curated shared surfaces.
- Root `.idea/` is a machine-local PyCharm state surface and MUST remain fully
  untracked. Reviewed portable PyCharm settings MUST live under
  `configs/ide/pycharm/` and MAY be copied into local `.idea/`.
- Generated/runtime root trees such as `node_modules/`, `output/`, `test-output/`,
  `logs/`, `MagicMock/`, `caddy/`, and local package trees like
  `.python-user/` MUST NOT попадать в git-index.
- Legacy root compatibility carryovers such as `script-codex/` or
  `script-gemini/` MUST NOT be treated as approved tracked roots. If they exist
  locally, they remain untracked compatibility copies; canonical maintained
  entrypoints live under `scripts/ai/codex/**`, `scripts/ai/gemini/**`, and the
  reviewed root launcher/setup surfaces.
- Root `logs/` MUST NOT использоваться как canonical retained log sink.
  Long-lived local/runtime log outputs MUST route into `reports/logs/`; any
  reintroduced root `logs/` tree is local clutter unless an explicit structure
  governance decision says otherwise.
- Root-level ad-hoc Python scratch/test files such as `test_*.py` MUST NOT
  оставаться в корне даже как ignored local clutter. They SHOULD be deleted or
  moved under `tests/**` or `scripts/**` with an explicit owner.
- Noncanonical documentation roots such as `concepts/` MUST NOT оставаться
  tracked в корне; documentation content MUST жить под `docs/**`, а historical
  or foreign-format doc carryovers SHOULD переезжать в `docs/99-archive/**`.

Root allowlist интерпретируется как policy surface, а не как временный склад.
Если новый root-level файл существует только для инцидента, ручной проверки или
финального статуса волны, он не должен закрепляться в корне.

`.codex_tmp/` is a local scratch/cache surface and MUST remain untracked.
`.gemini/` may remain tracked only as the canonical Gemini runtime tree; local
runtime state and generated artifacts under `.gemini/` MUST still stay
untracked unless explicitly reclassified through structure governance.
`.jules/` is a local vendor workspace surface and MUST remain untracked unless
explicitly reclassified through structure governance.
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

### 0.3.1. Generated docs helper surfaces

- `docs/site/**` is a generated local publication-helper surface produced by
  documentation build tooling (see `mkdocs.yml`). It is non-normative,
  MUST NOT использоваться как source of truth, and SHOULD remain a local or
  ignored generated output unless a specific artifact family is explicitly
  ratified elsewhere.
- `docs/exports/**` is a generated documentation-export surface. Exported merged
  snapshots such as `docs/exports/*.merged.md` are non-normative helper outputs
  and MUST follow their generated-artifact routing policy rather than being
  treated as active documentation.
- New generated documentation helper outputs MUST be classified in
  `configs/quality/generated_artifact_routing.yaml` and SHOULD be reflected in
  `configs/quality/repo_structure_catalog.yaml` when they represent a stable
  repo-level surface family.

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
- `data/**` — runtime/control-plane/data retention surface, including
  `data/debug_exports/**` debug evidence bundles

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

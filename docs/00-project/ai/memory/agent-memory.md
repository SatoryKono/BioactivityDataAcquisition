______________________________________________________________________

Version: 1.0.16
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-24'

______________________________________________________________________

# Agent Memory — BioETL Project

*Статус: internal-published (Internal / Extended)*

*Версия: 1.0.17 | Дата: 2026-07-24 | Синхронизировано с Codex ORCHESTRATION.md v4.3, RULES.md v6.1.5*

> **Runtime note:** для Codex source-of-truth orchestration живёт в `.codex/agents/ORCHESTRATION.md`; другие runtimes могут сохранять отдельные runtime-specific copies и не обязаны совпадать побайтно с Codex surface.

> **Surface note:** этот файл является project memory entry point внутри
> `docs/00-project/ai/memory/`; role-specific `memory-py-*.md` sheets дополняют
> его, а не заменяют runtime source или canonical governance docs.
>
> **Governance note:** version markers в memory — это navigation hints.
> Решения и проверки MUST подтверждаться по актуальным canonical surfaces:
> `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`,
> `docs/01-requirements/REQUIREMENTS.md`, accepted ADRs в
> `docs/02-architecture/decisions/`, `AGENTS.md`, active runtime source files.

> **Назначение**: Полный контекст для быстрого онбординга новой AI-сессии в BioETL.
> При старте новой сессии — попроси агент прочитать этот файл:
> `Прочитай docs/00-project/ai/memory/agent-memory.md и следуй его инструкциям.`

> **Daily workflow note:** для ежедневной инженерной работы используй
> canonical memory workflow из `src/memory/DAILY_WORKFLOW.md`:
> `python -m memory.tooling.workflow pre-task ...`
> перед задачей и
> `python -m memory.tooling.workflow post-task ...`
> после задачи. Session/summary notes должны жить в `src/memory/episodic/`,
> а durable lessons — промоутиться в `src/memory/curated/`.
> Workflow-time refresh теперь обязан быть surface-aware: timeline recovery не
> должна ждать full RAG rebuild, а временный RAG refresh должен оставаться
> bounded и query-focused вне canonical in-repo manifest lanes. Canonical full
> RAG живёт в rebuild-only `src/memory/derived/rag/manifests/`; retrieval
> допускается только после проверки catalog/chunk pair, source content,
> eligible source set и source identity.
> На регулярной cadence и перед release/governance review запускай
> `python -m memory.tooling.workflow review-curated`
> и архивируй superseded curated notes вместо тихого накопления stale memory.
> Episodic density по умолчанию проверяется через policy-backed prune dry-run:
> `max_active=1000`, review cadence `7` days. Versioned templates из
> `src/memory/episodic/templates/` не входят в prune/density scan.

______________________________________________________________________

## 1. Проект BioETL — Краткая Справка

**Назначение**: ETL-фреймворк для данных биоактивности из научных баз данных.

| Аспект          | Значение                                                                          |
| --------------- | --------------------------------------------------------------------------------- |
| Архитектура     | Hexagonal (Ports & Adapters) + Medallion (Bronze→Silver→Gold) + DDD               |
| Deployment      | Local-Only (ADR-010) — Docker optional adjunct, not required runtime              |
| Провайдеры      | ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar (7 шт.)     |
| ADR             | Текущий набор в `docs/02-architecture/decisions/`; ADR-008 исторически superseded |
| Coverage target | ≥85% overall, ≥90% domain                                                         |
| RULES.md        | v6.1.5 (read `Version:` header in file)                                         |

### Ключевые файлы

| Артефакт                                    | Путь                                                   |
| ------------------------------------------- | ------------------------------------------------------ |
| Правила проекта (Конституция)               | `docs/00-project/RULES.md`                             |
| Правила оркестратора и runtime policy       | `AGENTS.md`                                            |
| Инструкции для Claude                       | `docs/00-project/ai/agents/guides/CLAUDE.md`           |
| Персона агента                              | `docs/00-project/ai/agents/guides/AGENT.md`            |
| Claude compact context (runtime-specific)   | Claude runtime compact context (auto-loaded)           |
| Claude self-review rules (runtime-specific) | runtime self-review rules file                         |
| Оркестрация субагентов                      | `.codex/agents/ORCHESTRATION.md`                       |
| Папка с промтами проекта                    | `docs/00-project/ai/prompts/`                          |
| Глоссарий                                   | `docs/00-project/glossary.md`                          |
| ADR                                         | `docs/02-architecture/decisions/`                      |
| Domain Ports                                | `src/bioetl/domain/ports/`                             |
| Adapters                                    | `src/bioetl/infrastructure/adapters/{provider}/`       |
| Pipelines                                   | `src/bioetl/application/pipelines/`                    |
| Bootstrap                                   | `src/bioetl/composition/bootstrap/`                    |
| Configs (unified)                           | `configs/entities/{provider}/{entity}.yaml`            |
| Configs (composite)                         | `configs/composites/{entity}.yaml`                     |
| Dashboard extension guide (LLM)             | `docs/03-guides/dashboards/dashboard-extension-llm.md` |
| Docker quickstart (optional)                | `docs/DOCKER_QUICKSTART.md`                            |
| Docker setup / recovery (optional)          | `docs/DOCKER_SETUP.md`                                 |
| Stable Docker launcher (Windows)            | `scripts/ops/runtime/docker/ensure-stable.ps1`         |
| Docker host harden + watchdog (Windows)     | `scripts/ops/runtime/docker/harden-desktop-host.ps1` / `watchdog-docker-stable.ps1` |
| Pipeline/workflow run reports               | `docs/04-reference/reports/run-reports.md`             |
| Run-report contracts                        | `configs/contracts/reports/`                           |

### Evidence anchors

При структурных выводах и roadmap-решениях сначала сверяйся с актуальными evidence packs:

| Topic                                     | File                                                                                                            |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| File structure baseline                   | `docs/reports/evidence/project-file-structure/SUMMARY.md`                                                       |
| File structure decisions                  | `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`                                          |
| Package topology baseline                 | `docs/reports/evidence/project-package-topology/SUMMARY.md`                                                     |
| Package topology synthesis                | `docs/reports/evidence/project-package-topology/03-synthesis/SYN-project-package-topology.md`                   |
| Topology vs governance cross-synthesis    | `docs/reports/evidence/project-package-topology/03-synthesis/CROSS-SYNTHESIS-topology-vs-governance-signals.md` |
| Package topology decisions                | `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`                                        |
| Governance signals baseline               | `docs/reports/evidence/governance-signals/SUMMARY.md`                                                           |
| Governance signals decisions              | `docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md`                                              |
| Compatibility registry refactor evidence  | `docs/reports/evidence/compatibility-registry-refactor/SUMMARY.md`                                              |
| Compatibility registry refactor decisions | `docs/reports/evidence/compatibility-registry-refactor/04-decisions/SUMMARY.md`                                 |

Короткая operational rule:

- package count сам по себе не запускает structural wave;
- hotspot calibration по умолчанию идёт на уровне package family, а не whole layer;
- topology подсказывает, где смотреть; governance signals подсказывают, где действовать.
- compatibility registry использует YAML SSOT + shared loader + generated snapshot как baseline;
- freeze guards по умолчанию считаются отдельным import-discipline/removal-policy слоем и не должны автоматически мигрировать в shared loader.

### Technical debt tracking defaults

При любых file edits агент по умолчанию должен:

- отличать `exemption debt` от `hotspot inventory`;
- проверять применимые debt registries в
  `configs/quality/debt_scorecard.yaml`:
  `file_size_limits`, `function_complexity`, `function_length`, `class_size`,
  `class_method_count`, `god_object`, `domain_complexity`;
- для путей внутри named hotspot families смотреть family-level параметры
  (`duplication_clusters`, `files_ge_250_loc`, `max_internal_fan_in`,
  related growth caps) и не допускать тихой деградации;
- не вводить новый exemption без обновления
  `configs/quality/architecture_metric_exemptions.yaml` с required metadata и
  без сохранения scorecard sync;
- в closeout фиксировать debt outcome по затронутым файлам:
  `improved`, `unchanged` или `worsened`.

### Qodo-reconciled change gates (2026-07-16)

Каноническая нормализация находится в `RULES.md` §4.5. Источник — broad
best-effort semantic extraction для
`/SatoryKono/BioactivityDataAcquisition/`: 128 successful hits, 66 unique
Qodo IDs после deduplication. Это не полный export: endpoint
`POST /rules/search` ограничивает `top_k` значением 20. Qodo severity для всех
записей отсутствовала и хранится как `UNSPECIFIED`; агент **не должен**
выводить severity самостоятельно.

Перед завершением changeset проверь применимые группы:

- secrets отсутствуют во всех tracked surfaces и logs; `.env`/`.env.*` не
  затронуты без explicit per-task user approval, а ignore/package protections
  не ослаблены;
- critical config modes required, enum-like values validated, YAML key order
  deterministic, Qodo config keys/schema официально поддерживаются;
- public interfaces полностью типизированы; `Any` не скрывает type defects и
  остаётся только документированным boundary;
- outputs stable/canonical/UTC, artifact writes выполняются через tmp +
  `os.replace()`, merge/upsert keyed by stable primary/business key;
- при изменении `src/bioetl/**/*.py` обновлён module coverage inventory hash;
  debt budgets, thresholds и exclusions не увеличены;
- behavior changes имеют regression tests, assertions не ослаблены, test
  time/random/network контролируются fixtures/mocks/VCR;
- contributor-facing и breaking CLI/API/schema/config changes синхронно
  обновляют active docs, migration notes, changelog/version impact;
- constructor DI, composition-only wiring, inward imports, pure domain,
  adapter delegation, naming suffixes и `bioetl.domain.ports` facade
  соблюдены;
- runtime logging structured, provider/runtime HTTP идёт через
  `UnifiedHTTPClient`;
- Silver/Gold используют Delta Lake; exact final DataFrame проходит Pandera
  validation непосредственно перед write, Gold validation strict/fail-closed.

### Docker / WSL (optional adjunct, Windows hosts)

- Docker is **not** required for ordinary tests/runtime (ADR-010). When used:
  default surface = **main** health server `:8000`; monitoring opt-in;
  Loki/Tempo/Quarantine Explorer UI removed from compose.
- Crash pattern: free host RAM &lt; ~4 GiB + thrash → `docker-desktop` WSL
  **Stopped** → missing `dockerDesktopLinuxEngine` npipe.
- Prefer:
  `.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j`
  after flap: add `-RestartWsl`.
- Host class defaults: WSL `memory=6GB`, main/neo4j mem_limit **768m**,
  never multi-stack `--build` / `--force-recreate` thrash.
- Curated lesson: `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`

### Run reports + governance closeouts

- Post-run reports: `pipeline_run_report_v1` / `workflow_run_report_v1` under
  `reports/run-reports/`; guide `docs/04-reference/reports/run-reports.md`.
- After `src/bioetl/**` writes: refresh module-coverage inventory hash, topology
  SUMMARY, debt gates, then pin `evidence_surface_sha256` (last), and if tests
  changed pin `test_telemetry_baseline.yaml` `source_tree_sha256`.
- Curated lesson: `src/memory/curated/lessons/run-reports-and-governance-hash-refresh.md`
- **ЗАПРЕЩЕНО** поднимать tech-debt budgets, чтобы закрыть stale-hash gates.

### Быстрые команды

```bash
make lint          # ruff + mypy
make test          # Локальный стабильный suite с coverage (без E2E)
make test-architecture  # Архитектурные тесты
make install       # Установка зависимостей
make run-local     # Сэмпловый pipeline-run (chembl_activity, limit=10)
```

Для mixed Windows + WSL checkout предпочитай OS-specific wrappers:

> **Project venv preference:** все Python-команды в этом checkout запускай
> через соответствующее проектное окружение: `.venv/bin/python` в WSL и
> `.venv-win/Scripts/python.exe` (или Windows wrapper, который его выбирает)
> в Windows. Не полагайся на bare `python` из `PATH`.

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
bash scripts/engineering/dev/run_mypy.sh
```

### Unified Script Entry Points

Все скрипты доступны через `python -m scripts.<group> <command>`.
После `uv sync` предпочитай запуск через `uv run python -m scripts.<group> <command>`.
Для mixed Windows + WSL checkout используй OS-specific окружение:
`.venv-win` в PowerShell и `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` в WSL.
На Windows PowerShell mixed-checkout wrappers поддерживаемый дефолт `-n 1`;
использовать больше воркеров допускается только через явный
`BIOETL_PYTEST_WINDOWS_XDIST_WORKERS=<n>` override.
При активированном подходящем окружении допускается и прямой `python -m ...`.

| Group                             | Entry Point                                        | Назначение                                  |
| --------------------------------- | -------------------------------------------------- | ------------------------------------------- |
| `scripts.engineering.qa`          | `uv run python -m scripts.engineering.qa`          | Quality checks: naming, C901, terminology   |
| `scripts.engineering.ci`          | `uv run python -m scripts.engineering.ci`          | CI pipeline: pytest runner, quality gates   |
| `scripts.engineering.baselines`   | `uv run python -m scripts.engineering.baselines`   | Baseline maintenance for engineering checks |
| `scripts.schema`                  | `uv run python -m scripts.schema`                  | Schema/config validation и генерация        |
| `scripts.ops.data`                | `uv run python -m scripts.ops.data`                | Data integrity: checksums, delta, data dir  |
| `scripts.engineering.qa.vcr`      | `uv run python -m scripts.engineering.qa.vcr`      | VCR governance: placement, naming, secrets  |
| `scripts.docs`                    | `uv run python -m scripts.docs`                    | Documentation: links, drift, docstrings     |
| `scripts.diagrams`                | `uv run python -m scripts.diagrams`                | Diagram lint, check, fix, render            |
| `scripts.engineering.repo`        | `uv run python -m scripts.engineering.repo`        | Repo hygiene: inventory, catalog, versions  |
| `scripts.ops`                     | `uv run python -m scripts.ops`                     | Ops: salt rotation, Grafana, deploy         |
| `scripts.engineering.dev`         | `uv run python -m scripts.engineering.dev`         | Dev setup, test runner, mock metrics        |
| `scripts.engineering.diagnostics` | `uv run python -m scripts.engineering.diagnostics` | Debug: cleanup, pandera, storage            |

Каждая группа поддерживает `--help` и `<command> --help`. Скрипты также доступны напрямую: `python scripts/engineering/qa/naming_audit.py`.

#### Ключевые команды по задачам

```bash
# Архитектурная валидация
uv run python -m scripts.engineering.qa check-naming --check
uv run python -m scripts.engineering.qa check-c901
uv run python -m scripts.engineering.repo check-inventory --check

# Config/schema
uv run python -m scripts.schema validate-configs
uv run python -m scripts.schema check-invariants
uv run python -m scripts.schema generate-pipeline --check

# Документация
uv run python -m scripts.docs check-links --links --specs --configs
uv run python -m scripts.docs check-drift --ports --classes
uv run python -m scripts.docs check-docstrings --summary

# Диаграммы
uv run python -m scripts.diagrams lint
uv run python -m scripts.diagrams check-quality-gates
uv run python -m scripts.diagrams render-pdf

# Data integrity
uv run python -m scripts.engineering.qa.vcr check-placement
uv run python -m scripts.ops.data checksums --generate

# CI / Quality gates
uv run python -m scripts.engineering.ci quality-gate
uv run python -m scripts.engineering.ci run-tests

# Baselines
uv run python -m scripts.engineering.baselines dq-baseline --dry-run
```

### Daily Memory Workflow

Перед обычной engineering/audit задачей не изобретай собственный memory-loop.
Используй стандартный порядок:

1. `python -m memory.tooling.workflow pre-task ...`
1. `catalog -> graph -> rag -> source`
1. правка или аудит canonical source
1. `python -m memory.tooling.workflow post-task ...`
1. promotion только для durable knowledge
1. по регулярной cadence и перед release/governance checkpoints:
   `python -m memory.tooling.workflow review-curated`

Минимальный пример:

```bash
python -m memory.tooling.workflow pre-task \
  --task-id task-123 \
  --title "Investigate chembl activity ownership"

python -m memory.tooling.workflow post-task \
  --task-id task-123 \
  --title "Investigate chembl activity ownership" \
  --summary "Verified source surfaces and refreshed memory."
```

### Dashboard-specific note

Если задача затрагивает `grafana/dashboards/*.json`, dashboard links,
drilldown в Loki/Tempo или operator flow между `1. Overview`, `2. Runtime`,
`3. Provider Health`, `4. Data Quality`, сначала прочитай:

- `docs/03-guides/dashboards/dashboard-extension-llm.md`

______________________________________________________________________

## 2. Архитектурные Инварианты (CRITICAL)

### 2.0 Критическое Governance Правило

**ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**

- Технический долг может только **уменьшаться** или **оставаться неизменным**
- Увеличение бюджетов тех. долга (файловые лимиты, сложность функций, размер классов и т.д.) **СТРОГО ЗАПРЕЩЕНО**
- При любых изменениях проверяйте `configs/quality/debt_scorecard.yaml` и не допускайте деградации лимитов
- Для hotspot families используйте family-level параметры и не допускайте тихой деградации
- Это правило применяется ко всем агентам и всем типам задач без исключения

### 2.1 Матрица импортов

| From \\ To         | domain | application | infrastructure | composition | interfaces |
| ------------------ | :----: | :---------: | :------------: | :---------: | :--------: |
| **domain**         |   OK   |     NO      |       NO       |     NO      |     NO     |
| **application**    |   OK   |     OK      |       NO       |     NO      |     NO     |
| **infrastructure** |   OK   |     NO      |       OK       |     NO      |     NO     |
| **composition**    |   OK   |     OK      |       OK       |     OK      |     NO     |
| **interfaces**     |   OK   |     OK      |       NO       |     OK      |     OK     |

> Direct `interfaces -> infrastructure` imports are forbidden by ADR-005 and
> `.importlinter`; interfaces must obtain concrete runtime wiring through
> composition-owned entrypoints.

> Infrastructure может импортировать ВСЁ из domain (ports, types, exceptions, entities, config).
> Ports MUST импортироваться через фасад: `from bioetl.domain.ports import X`.

### 2.2 Domain Purity

Запрещено в domain: `import requests/httpx/aiohttp`, `open()`, `import structlog`, database clients.

### 2.3 DI через конструктор

- Запрещено: `self.client = ConcreteClass()` в application/domain
- Запрещено: Service Locator, global registry lookup и Factory в business logic
- Factories и concrete wiring разрешены только в `composition/`
- `structlog` только через `LoggerPort` (кроме `infrastructure/observability/`)

### 2.4 Medallion

- Bronze: JSONL + zstd, append-only, 90d retention
- Silver: **Delta Lake ONLY** (raw Parquet запрещён), merge/upsert по `content_hash`, ACID
- Gold: **Delta Lake ONLY**, SCD Type 2 или documented overwrite/append contract
- Silver/Gold: exact final DataFrame валидируется Pandera непосредственно перед
  write; Gold — `strict=True` и fail-closed
- Content Hash: `sha256(provider + canonical_json(record))`
- DQ пороги: soft=5%, hard=20%

### 2.5 Valid Exceptions (НЕ нарушения)

- `TYPE_CHECKING` imports
- `param: T | None = None` для DI
- NoOp implementations (Null Object)
- Re-exports для compatibility
- `MemoryLock` (ADR-010)
- Int→Float coercion в Gold schemas
- Large files с proper delegation
- `domain.types` / `domain.exceptions` everywhere

______________________________________________________________________

## 3. Субагенты — Как Вызывать

### 3.1 Доступные субагенты

Вызов: `spawn_agent(agent_type="default" | "explorer" | "worker", message="...")`

|  #  | `subagent_type` | Модель | Зона записи                     | Назначение                                                         |
| :-: | --------------- | ------ | ------------------------------- | ------------------------------------------------------------------ |
|  I  | `py-audit-bot`  | opus   | read-only                       | Baseline/final аудит, code review, arch boundaries, API validation |
| II  | `py-plan-bot`   | opus   | read-only                       | Декомпозиция на RF-\*, DAG зависимостей, composite pipeline design |
| III | `py-test-bot`   | sonnet | `tests/`                        | Baseline/final/retest тесты, coverage ≥85%, VCR                    |
| IV  | `py-config-bot` | sonnet | `configs/`                      | Pipeline/DQ/filter YAML configs, composite, gap remediation        |
|  V  | `py-debug-bot`  | opus   | `src/bioetl/`, `tests/` (fixes) | RCA падений, DBG-\* итерации (макс 5), mypy/import/runtime         |
| VI  | `py-doc-bot`    | sonnet | `docs/`, docstrings             | ADR, CHANGELOG, docstrings, diagrams, doc-code sync                |

> Production-код пишем напрямую через Edit/Write (без отдельного субагента).

### 3.2 Полные спецификации и память субагентов

Перед вызовом субагента — прочитай его спецификацию и память:

```
.codex/agents/py-audit-bot.md    — входы, выходы, чеклисты, scoring
.codex/agents/py-plan-bot.md     — шаблоны планов, RF-* routing
.codex/agents/py-test-bot.md     — test selection strategy, VCR management
.codex/agents/py-config-bot.md   — шаблоны YAML, иерархия configs
.codex/agents/py-debug-bot.md    — методология отладки, классификация ошибок
.codex/agents/py-doc-bot.md      — структура docs, ADR management, diagrams
.codex/agents/ORCHESTRATION.md   — полный workflow, матрица взаимодействий
```

**Специализированная память (фокус на области работы агента):**

```
docs/00-project/ai/memory/memory-py-audit-bot.md   (v1.0.3) — import matrix, anti-patterns, naming, scoring, valid exceptions
docs/00-project/ai/memory/memory-py-plan-bot.md    (v1.0.2) — RF-* routing, DAG, composite design, parallelization, ADR
docs/00-project/ai/memory/memory-py-test-bot.md    (v1.0.2) — test structure, thresholds, VCR, failure classification
docs/00-project/ai/memory/memory-py-config-bot.md  (v1.0.2) — config hierarchy, templates, ADR compliance, composite rules
docs/00-project/ai/memory/memory-py-debug-bot.md   (v1.0.2) — error classification, debugging methodology, fix patterns
docs/00-project/ai/memory/memory-py-doc-bot.md     (v1.0.2) — doc structure, ADR management, CHANGELOG, docstrings, diagrams
docs/00-project/ai/memory/memory-py-architecture-debt-bot.md (v1.0.1) — architecture debt waves, exemption governance, closure gates
docs/00-project/ai/memory/memory-py-review-orchestrator.md   (v1.0.1) — sector review map, evidence rollup, severity calibration
docs/00-project/ai/memory/memory-py-test-swarm.md            (v1.0.1) — swarm decomposition, failure telemetry, flakiness protocol
```

Все memory sheets обновлены до версий v1.0.1-v1.0.3 на 2026-07-24 с синхронизированными guardrails по тех. долгу и evidence anchors.

### 3.3 Входы субагентов (обязательные параметры)

При вызове `spawn_agent(...)` или соответствующего runtime wrapper включай в `message`:

| Субагент      | MUST в prompt                                                                      |
| ------------- | ---------------------------------------------------------------------------------- |
| py-audit-bot  | `task_id`, `phase` (baseline/final/targeted), `scope` (файлы/модули)               |
| py-plan-bot   | `task_id`, `task_description`, опционально `user_plan`, `audit_baseline`           |
| py-test-bot   | `task_id`, `phase` (baseline/final/retest/new_tests), `plan`, `rf_ids`             |
| py-config-bot | `task_id`, `mode` (create/update/composite/validate/migrate), `provider`, `entity` |
| py-debug-bot  | `task_id`, `failing_test_report`, `stack_traces`, `rf_ids`, `phase`                |
| py-doc-bot    | `task_id`, `plan`, `refactoring_log`, `rf_ids`                                     |

### 3.4 Выходы (артефакты)

```
reports/{LLM}/review_{agent}_{YYYYMMDD}_{HHMM}[_{phase}].md
```

Единый контракт для итоговых отчётов:

- Все `py-*` профили сохраняют итоговые отчёты по пути выше.
- `phase` используется только там, где профиль явно различает `baseline` / `final` / `targeted` в имени файла.
- `LLM` = вызывающая модель, `agent` = логический профиль/skill.
- Дополнительные телеметрические артефакты MAY сохраняться рядом, но финальный отчёт должен использовать этот шаблон.

### 3.5 ID-системы

| Prefix  | Субагент      | Пример                         |
| ------- | ------------- | ------------------------------ |
| `RF-`   | py-plan-bot   | RF-001 — рефакторинг/изменение |
| `DBG-`  | py-debug-bot  | DBG-001 — debug-итерация       |
| `AUD-`  | py-audit-bot  | AUD-001 — audit finding        |
| `DOC-`  | py-doc-bot    | DOC-001 — doc update           |
| `FAIL-` | py-test-bot   | FAIL-001 — упавший тест        |
| `CFG-`  | py-config-bot | CFG-001 — config change        |

______________________________________________________________________

## 4. Стандартный Workflow

```
① py-audit-bot (baseline)     → review_py-audit-bot_{YYYYMMDD}_{HHMM}_baseline.md
② py-plan-bot (initial)       → review_py-plan-bot_{YYYYMMDD}_{HHMM}.md
③ py-test-bot (baseline)      → review_py-test-bot_{YYYYMMDD}_{HHMM}.md
   [если FAIL → py-debug-bot → py-test-bot (retest) цикл]
④ Реализация (параллельно):
   - напрямую (orchestrator)   → src/bioetl/
   - py-config-bot             → configs/
⑤ py-test-bot (final)         → review_py-test-bot_{YYYYMMDD}_{HHMM}.md
   [если FAIL → py-debug-bot → py-test-bot (retest) цикл ≤5]
⑥ py-doc-bot                  → review_py-doc-bot_{YYYYMMDD}_{HHMM}.md
⑦ py-audit-bot (final)        → review_py-audit-bot_{YYYYMMDD}_{HHMM}_final.md
   [если MUST findings → возврат к debug/plan]
```

### 4.1 Упрощённые режимы

| Режим                  | Workflow                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------- |
| **Quick-fix**          | test(baseline) → code(fix) → test(final) → doc(docstring only)                        |
| **Doc-only**           | doc-bot → audit(targeted, docs)                                                       |
| **Config-only**        | audit(targeted, config) → plan → config-bot → test(final) → audit(final)              |
| **New entity**         | plan → orchestrator(scaffold) → config-bot(3 configs) → test(new+final) → doc → audit |
| **Composite pipeline** | audit(baseline) → plan(composite) → config-bot → orchestrator → test → doc → audit    |

### 4.2 Параллелизация

- `py-test-bot (baseline)` || `py-audit-bot (baseline)` — оба read-only
- `orchestrator` || `py-config-bot` — разные файловые зоны
- `py-doc-bot` || `py-audit-bot (final)` — если doc не влияет на code audit

______________________________________________________________________

## 5. Skills (Навыки)

### 5.1 Проектные Skills и entrypoints

Механика вызова зависит от активного runtime. SSOT для проектных skills и
workflow-ролей в текущем репозитории находится в `.codex/skills/` и
`.codex/agents/`. Published mirrors под `docs/00-project/ai/skills/` и
runtime-specific copies в других деревьях не переопределяют этот источник.

| Skill / entrypoint       | Где смотреть SSOT                             | Назначение                       |
| ------------------------ | --------------------------------------------- | -------------------------------- |
| `agent-orchestration`    | `.codex/skills/agent-orchestration/`          | Координация multi-agent workflow |
| `py-audit-bot`           | `.codex/skills/py-audit-bot/`                 | Baseline/final audit             |
| `py-plan-bot`            | `.codex/skills/py-plan-bot/`                  | RF-планирование                  |
| `py-test-bot`            | `.codex/skills/py-test-bot/`                  | Post-change verification         |
| `py-doc-bot`             | `.codex/skills/py-doc-bot/`                   | Документационные правки          |
| `py-config-bot`          | `.codex/skills/py-config-bot/`                | Config/docs sync                 |
| `py-debug-bot`           | `.codex/skills/py-debug-bot/`                 | Failure triage                   |
| `py-review-orchestrator` | `.codex/skills/py-review-orchestrator/`       | Независимый double-check         |
| `py-test-swarm`          | `.codex/skills/py-test-swarm/`                | Иерархическое тестирование       |
| `new-pipeline`           | `.codex/skills/new-pipeline/`                 | Scaffolding pipeline             |
| `verify-architecture`    | `.codex/skills/verify-architecture/`          | Архитектурные проверки           |
| `documentation-audit`    | `.codex/skills/documentation-audit/`          | Аудит документации               |
| `architecture-guardian`  | `.codex/skills/public/architecture-guardian/` | Граничный архитектурный review   |

### 5.2 Runtime-specific conveniences

Другие runtime built-ins, slash-команды и прочие runtime-specific entrypoints
допустимы только как дополнительное удобство. Их нельзя считать каноническим
workflow для BioETL: приоритет у `.codex/agents/ORCHESTRATION.md`,
`.codex/skills/` и `AGENTS.md`.

Если нужна фактическая команда для текущего runtime, смотри его собственный
реестр команд/skills, а не эту память.

______________________________________________________________________

## 6. Runtime Integrations

Runtime-конфигурация зависит от активного AI-клиента и должна читаться из
его реестров, а не из статического списка в этой памяти.

| Runtime | Что проверять                                                                    |
| ------- | -------------------------------------------------------------------------------- |
| Codex   | `.codex/config.toml`, `.codex/settings.json`, `.codex/agents/`, `.codex/skills/` |
| Claude  | runtime-specific settings, agent registry, and skill registry                    |
| Gemini  | local-only Gemini settings/runtime helper docs; no tracked `.gemini/agents/` or `.gemini/skills/` tree on `main` |
| Copilot | `.github/copilot-instructions.md`, workspace MCP config                          |

### 6.1 MCP / Tool Policy

- Для текущего набора MCP/tooling проверяй активный runtime-конфиг, а не docs mirror.
- Для Codex используй `codex mcp list`, если нужен фактический список серверов в текущей сессии.
- Для других runtimes ориентируйся на их собственные registry/settings surfaces.
- При расхождениях runtime-реестры имеют приоритет над документационными копиями.

______________________________________________________________________

## 7. Native Agent Roles (Codex Runtime)

В Codex runtime для логических профилей `py-*` используются native agent roles:

| `agent_type` | Назначение                               | Когда использовать                              |
| ------------ | ---------------------------------------- | ----------------------------------------------- |
| `default`    | Аудит, планирование, оркестрация, review | Baseline/final audit, RF-plan, docs/code review |
| `explorer`   | Read-only discovery                      | Инвентаризация, поиск фактов, узкие проверки    |
| `worker`     | Изолированная write-zone работа          | Docs/config/test edits с явной зоной владения   |

Runtime-specific helpers вне Codex допустимо хранить как parallel runtime context.
Для текущего project workflow BioETL их нельзя считать SSOT: приоритет у
`.codex/agents/ORCHESTRATION.md` и `AGENTS.md`.

______________________________________________________________________

## 8. Naming Conventions (Быстрая Справка)

### Классы

| Тип         | Suffix         | Пример                |
| ----------- | -------------- | --------------------- |
| Factory     | `*Factory`     | `PipelineFactory`     |
| Client      | `*Client`      | `ChEMBLClient`        |
| Port        | `*Port`        | `DataSourcePort`      |
| Service     | `*Service`     | `ValidationService`   |
| Transformer | `*Transformer` | `CompoundTransformer` |
| Error       | `*Error`       | `ValidationError`     |
| Schema      | `*Schema`      | `CompoundGoldSchema`  |
| Config      | `*Config`      | `RuntimeConfig`       |

### Функции

| Prefix                     | Назначение           |
| -------------------------- | -------------------- |
| `get_*`                    | Локальные данные     |
| `fetch_*`                  | Сетевые/I/O операции |
| `iter_*`                   | Генераторы           |
| `create_*` / `build_*`     | Создание объектов    |
| `validate_*`               | Валидация            |
| `is_*` / `has_*` / `can_*` | Boolean queries      |

______________________________________________________________________

## 9. Протокол Двойной Верификации

> **ОБЯЗАТЕЛЬНО** перед любым утверждением об архитектуре:

1. Прочитай **реальный код** (не предполагай)
1. Проверь каждый finding **дважды** (размер, структура, делегирование)
1. Указывай **точные ссылки** `файл:строка`
1. Сверяйся со списком **Valid Exceptions** (§2.5)

______________________________________________________________________

## 10. Что Делать в Первую Очередь в Новом Чате

1. **Прочитать этот файл** — ты уже здесь
1. **Прочитать `AGENTS.md`** — правила оркестратора, ограничения и tooling
1. **Прочитать `.codex/agents/ORCHESTRATION.md`** — текущий workflow и роли
1. **При использовании логического профиля** — прочитать `.codex/agents/py-{name}.md`
1. **При scaffolding** — использовать workflow `new-pipeline`
1. **Перед завершением code/docs changes** — прогнать `verify-architecture` или эквивалентный project check
1. **Только если активный runtime = Claude** — дополнительно прочитать Claude runtime compact context (auto-loaded)
1. **Только если активный runtime = Claude** — дополнительно прочитать runtime self-review rules file

### Команда для загрузки полного контекста:

```
Прочитай следующие файлы и следуй их инструкциям:
1. docs/00-project/ai/memory/agent-memory.md
2. AGENTS.md
3. .codex/agents/ORCHESTRATION.md
4. .codex/agents/py-{name}.md  # если используется логический профиль
```

______________________________________________________________________

*Этот файл — живой документ. Обновляй при изменении архитектуры, добавлении новых агентов или правил.*

Синхронизировано с ORCHESTRATION.md v4.3

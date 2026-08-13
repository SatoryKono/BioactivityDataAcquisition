---
id: prompt.observability.grafana-six.evidence
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - BRANCH
  - COMMIT_SHA
  - LANGUAGE
  - MONITORING
  - GRAFANA_URL
  - APP_BASE_URL
  - WORKFLOW
  - PIPELINE
  - RUN_TYPE
  - RUN_ID
  - OUTPUT_DIR
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/bi-check-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/grafana-six-contract.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - grafana/dashboards
  - grafana/README.md
  - grafana/provisioning
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/dashboard-inventory.md
  - docs/03-guides/dashboards/dashboard-v2-usage.md
  - docs/03-guides/dashboards/contracts/dashboard-inventory.yaml
  - docs/03-guides/dashboards/contracts/selector-contracts.yaml
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Inventing metric names, UIDs, or panel IDs
  - Treating No data as a defect without scope proof
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Mixing render-environment blockers with dashboard defects
  - Opening GitHub issues from a read-only evidence pass
  - Substituting visual findings for data semantics or vice versa
tags: [observability, grafana, audit, evidence, read-only, operator]
summary: Read-only Grafana evidence pack — inventory, preflight, scopes, renders
max_body_lines: 450
---

Промт 0. Подготовка аудита и сбор evidence pack

Назначение

Запускается первым. Формирует единый воспроизводимый набор доказательств для всех последующих аудитов. Без этого этапа разные агенты почти неизбежно проверят разные time range, variables и состояния datasource, а затем торжественно сравнят несравнимое.

НАЧАЛО ПРОМТА

Ты - Principal Grafana Audit Orchestrator, Observability Evidence Engineer и BioETL Architecture Reviewer.

Задача

Подготовь read-only evidence pack для аудита всех дашбордов в {{DASHBOARD_SCOPE}} по состоянию репозитория {{REPOSITORY_ROOT}}, ветка {{BRANCH}}, коммит {{COMMIT_SHA}}.

Не оценивай дизайн и не формируй remediation backlog на этом этапе. Твоя задача - зафиксировать проверяемое состояние, границы доступности и воспроизводимые входные данные.

Обязательные источники

Сначала изучи:

AGENTS.md и нормативный индекс проекта;

grafana/dashboards/*.json;

grafana/README.md;

docs/03-guides/dashboards/dashboard-inventory.md;

docs/03-guides/dashboards/dashboard-audit-checklist.md;

docs/03-guides/dashboards/design-system.md;

docs/03-guides/dashboards/contracts/dashboard-inventory.yaml;

docs/03-guides/dashboards/contracts/navigation-links.yaml;

docs/03-guides/dashboards/contracts/selector-contracts.yaml;

panel-specific docs в docs/03-guides/dashboards/panels/;

provisioning и datasource definitions в grafana/provisioning/.

Dashboard JSON является источником истины для фактической структуры. Документацию используй для проверки контрактов и выявления drift.

Этап 1. Зафиксируй исходное состояние

Зафиксируй:

repository path;

branch;

commit SHA;

dirty/clean working tree;

Grafana version, если доступна;

timezone браузера и dashboard timezone;

timestamp сбора evidence в UTC.

Перечисли все фактически найденные dashboard JSON.

Для каждого дашборда извлеки:

filename;

UID;

title;

tags;

default time range;

refresh interval;

variables;

datasource families;

количество rows и panels;

panel IDs и titles;

panel types;

navigation panel и links;

наличие repeated panels/library panels;

schemaVersion.

Не используй запомненный список дашбордов. Если inventory docs расходятся с JSON, зафиксируй CONTRADICTION.

Этап 2. Выполни preflight

Используй канонические repo commands, если они доступны:

uv run python -m scripts.ops check-grafana-audit-preflight --json --skip-screenshot-check
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates

Дополнительно зафиксируй доступность:

Grafana API;

server-side render;

browser fallback;

Prometheus;

HTTP control-plane backend;

HTTP quarantine backend;

Loki и Tempo handoff, если они входят в проверяемый scope.

При ошибке не обходи canonical tooling случайными curl-экспериментами как основным доказательством. Укажи точный failing check и классифицируй блокер как ENVIRONMENT, AUTH, DATASOURCE, RENDER_RUNTIME или UNKNOWN.

Этап 3. Сформируй тестовые scopes

Подготовь минимум четыре сценария:

POPULATED: известный scope с фактическими данными.

ZERO_EXPECTED: корректный scope, где ожидается нулевое значение хотя бы для части event counters.

NO_DATA_EXPECTED: корректный scope без применимой series или записей.

INVALID_OR_UNAVAILABLE: невалидный selector chain либо намеренно недоступный backend для проверки различимости ошибки.

Для каждого сценария зафиксируй:

workflow;

pipeline;

run type;

run ID, если применим;

provider;

time range;

from/to timestamps;

ожидаемый класс результата, но не конкретное значение без доказательств.

Не передавай высококардинальные forensic identifiers в Prometheus labels и не считай их обязательным способом фильтрации summary panels.

Этап 4. Выполни воспроизводимый render

Используй канонический renderer:

uv run python -m scripts.ops rerender-grafana \
  --timeout-seconds 90 \
  --output-dir {{OUTPUT_DIR}}

Для всех dashboard first screens создай render минимум в:

1366x768;

1440x900;

1920x1080.

Для полной вертикальной структуры создай full-page render в 1920x1080 или эквивалентный набор сегментов с перекрытием.

Не меняй variables между viewport renders одного сценария.

Для panel-level renders сохраняй panel ID, viewport, scenario и time range в имени файла или manifest.

Зафиксируй browser zoom 100%. Отдельно, если технически возможно, проверь 125% для first screen.

Этап 5. Выполни live reviewed panel audit

Если live data доступна, запусти:

uv run python -m scripts.ops audit-live-grafana \
  --workflow {{WORKFLOW}} \
  --pipeline {{PIPELINE}} \
  --run-type {{RUN_TYPE}} \
  --run-id {{RUN_ID}} \
  --app-base-url {{APP_BASE_URL}} \
  --output {{OUTPUT_DIR}}/live-panel-audit.json

Особенно зафиксируй панели, связанные с:

идентификаторами запуска;

processed records;

checkpoint freshness;

DQ freshness;

zero-vs-no-data semantics;

Silver Reject Explorer denominator behavior;

control-plane HTTP data.

Формат результата

Подготовь следующие разделы:

Audit Identity.

Dashboard Inventory.

Datasource Availability Matrix.

Scenario Matrix.

Render Manifest.

Automated Checks.

Blocked Evidence.

Known Contradictions.

Handoff to Prompts 1-3.

Минимальная таблица dashboard inventory:

Dashboard file

UID

Title

Panels

Variables

Datasources

Default range

Render status

Минимальная таблица evidence manifest:

Evidence ID

Dashboard UID

Scenario

Viewport

Time range

Variables

Artifact

Status

Критерии завершения

Этап завершен, когда:

каждый dashboard из scope сопоставлен с JSON и актуальным UID;

для каждого dashboard есть хотя бы один reproducible render или точный blocker;

test scopes документированы;

доступность каждого datasource классифицирована;

автоматические проверки перечислены с фактическими результатами;

последующие аудиторы смогут повторить тот же render и запросы.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`

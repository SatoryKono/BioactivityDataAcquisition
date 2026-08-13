---
id: prompt.observability.grafana-six.reverify
version: 1.0.1
status: deprecated
class: operator-paste
owner: BioETL Team
successor: prompt.observability.grafana-audit.regression
runtimes: [grok, codex, any]
params:
  - SCOPE
  - BRANCH
  - COMMIT_SHA
  - LANGUAGE
  - MONITORING
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
tags: [observability, grafana, audit, reverify, read-only, operator]
summary: Independent Grafana re-audit after fixes — before/after evidence
max_body_lines: 450
---

Промт 5. Контрольный аудит после исправлений

Назначение

Используется после реализации. Проверяет не только закрытие исходных finding, но и отсутствие новых регрессий в соседних панелях, variables и dashboard contracts.

НАЧАЛО ПРОМТА

Ты - Independent Grafana Regression Auditor и BioETL Observability Verification Reviewer.

Входы

исходный evidence pack;

подтвержденный реестр DASH-AUD-*;

commit до исправлений;

commit после исправлений;

перечень измененных файлов;

результаты реализации и тестов.

Задача

Проведи независимый read-only re-audit. Не принимай статус issue или текст отчета реализации как доказательство закрытия.

Этап 1. Проверь scope изменений

Сравни dashboard JSON структурно, не только текстовым diff.

Зафиксируй измененные:

panel IDs;

grid positions;

queries;

variables;

units;

thresholds;

mappings;

links;

datasource UIDs;

default range/refresh;

docs/contracts.

Выяви accidental drift вне заявленного scope.

Этап 2. Пересоздай evidence

Повтори preflight, renders и live scenarios с теми же:

viewport;

variables;

time ranges;

data scopes;

browser zoom;

datasource endpoints.

Если данные изменились естественным образом, сравни semantics и invariants, а не абсолютные значения.

Этап 3. Проверь каждое finding

Для каждого DASH-AUD-* присвой:

CLOSED;

PARTIALLY_CLOSED;

NOT_FIXED;

REGRESSED;

BLOCKED;

INVALIDATED_BY_NEW_EVIDENCE.

Укажи before/after evidence и выполненный acceptance criterion.

Этап 4. Проверь соседние регрессии

Обязательно проверь:

first-screen overlaps;

navigation links и variable propagation;

selector All/empty behavior;

zero/no-data/backend error;

query duplication;

units/decimals;

status colors и mappings;

table transformations;

datasource health;

docs/YAML parity;

high-cardinality label drift;

render на 1366x768 и 1920x1080.

Этап 5. Выполни автоматические проверки

Минимум:

uv run python -m scripts.ops check-grafana-audit-preflight --json --skip-screenshot-check
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
uv run python -m pytest -q tests/integration/test_grafana_config.py
uv run python -m pytest -q tests/integration/test_grafana_dashboard_links.py
uv run python -m pytest -q tests/integration/test_grafana_selector_contract.py
uv run python -m pytest -q tests/integration/test_grafana_variable_reference.py
uv run python -m pytest -q tests/integration/test_grafana_dashboard_first_screen_contract.py

Запускай только команды, реально существующие в проверяемом commit. Отсутствующую команду не заменяй выдуманной.

Формат результата

Verification Identity.

Changed Surface Inventory.

Finding Closure Matrix:

Finding ID

Before

After

Acceptance criterion

Status

Evidence

Regression risk

New Regressions.

Automated Test Results.

Residual Gaps.

Final Verdict: PASS, PASS_WITH_RESIDUALS, FAIL, BLOCKED.

Критерии качества

Ни один finding не закрыт только по наличию commit.

Before/after сравнение воспроизводимо.

Проверены сценарии zero/no-data/error.

Проверен narrow viewport.

Новые проблемы не маскируются успехом основной задачи.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`

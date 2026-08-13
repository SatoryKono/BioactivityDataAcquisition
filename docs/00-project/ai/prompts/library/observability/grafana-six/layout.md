---
id: prompt.observability.grafana-six.layout
version: 1.0.1
status: deprecated
class: operator-paste
owner: BioETL Team
successor: prompt.observability.grafana-audit.layout
runtimes: [grok, codex, any]
params:
  - SCOPE
  - BRANCH
  - COMMIT_SHA
  - LANGUAGE
  - VIEWPORT
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
tags: [observability, grafana, audit, layout, ia, read-only, operator]
summary: Read-only Grafana layout audit — composition, IA, sizes, navigation
max_body_lines: 450
---

Промт 2. Аудит расположения и состава панелей

Назначение

Проверяет информационную архитектуру, first-screen hierarchy, grid layout, размеры панелей, дублирование и полноту operator workflow. Цвета и шрифты рассматриваются только как факторы композиции.

НАЧАЛО ПРОМТА

Ты - Principal Grafana Dashboard Architect, Information Architecture Reviewer, Human Factors Engineer и BioETL Operator-Workflow Auditor.

Задача

Проведи исчерпывающий read-only аудит расположения, размеров, группировки и состава панелей для {{DASHBOARD_SCOPE}}.

Используй dashboard JSON, grid positions и renders из evidence pack. Не выводи layout только по screenshot: проверяй gridPos, row structure, collapsed state, repeated panels, links, variables и actual panel dimensions.

Основной вопрос аудита

Для каждого dashboard сначала сформулируй его фактический ONE BIG QUESTION одним предложением. Затем проверь, помогает ли first screen ответить на него за 5-10 секунд без прокрутки и без открытия Query Inspector.

Если dashboard пытается одновременно отвечать на несколько равноправных вопросов, зафиксируй это как architecture finding, а не просто как «слишком много панелей».

Этап 1. Инвентаризация panel roles

Классифицируй каждую панель:

NAVIGATION;

SCOPE_CONTEXT;

PRIMARY_VERDICT;

CURRENT_STATUS;

CURRENT_CAUSE;

RANGE_TREND;

BREAKDOWN;

DIAGNOSTIC_DETAIL;

FORENSIC_DETAIL;

FIRST_ACTION;

DRILLDOWN_HANDOFF;

DOCUMENTATION_HELP.

Для каждой панели укажи:

dashboard UID;

panel ID/title;

row/group;

gridPos x/y/w/h;

role;

вопрос, на который она отвечает;

уникальные operator facts;

основные dependencies;

целевой decision/action.

Этап 2. Проверь first screen

Проверь:

primary verdict above the fold;

текущий scope и selector context;

provenance/freshness/risk context;

first action;

различимость current state и selected-range evidence;

отсутствие noisy diagnostics на первом экране;

отсутствие дублированной navigation surface;

отсутствие vertical gaps, overlaps и случайных asymmetries;

предсказуемый порядок чтения слева направо и сверху вниз;

совместимость с 1366x768, 1440x900 и 1920x1080;

отсутствие ключевого KPI ниже fold из-за чрезмерной высоты header/text panels;

сохранение контекста при scroll.

Для first screen создай reading-order map с номерами 1..N.

Этап 3. Проверь tier hierarchy

Сопоставь фактическую структуру с целевой логикой:

Tier 1: ответ или verdict;

Tier 2: current context и причины;

Tier 3: selected-range evidence и trends;

Tier 4: diagnostic/forensic details и drilldowns.

Зафиксируй:

панели не своего tier;

смешение current и historical semantics;

диагностику, занимающую first-screen area;

supporting panels, поставленные выше primary verdict;

row groups, которые скрывают обязательный контекст;

expanded rows, создающие шум без operator value;

collapsed rows, скрывающие доказательства, необходимые для triage.

Этап 4. Оцени информационную плотность

Для каждой row/group рассчитай:

grid_area = sum(w * h) для панелей группы;

количество уникальных operator facts;

information_density = unique_facts / grid_area;

количество panel titles, повторяющих один и тот же факт;

долю площади, занятую navigation/help/empty whitespace;

число действий, доступных без scroll.

Правила подсчета:

Один факт считается уникальным только если он меняет решение оператора или локализует проблему.

Разные визуализации одной и той же величины не считаются двумя фактами без отдельного temporal или categorical значения.

Текстовый handoff не считается фактом, но считается action surface.

Плотность сравнивай прежде всего внутри одного dashboard family. Не используй универсальный порог без evidence.

Низкая плотность не всегда дефект: first-action и risk panels могут быть намеренно просторными.

Минимальная таблица:

Dashboard

Row/group

Panels

Unique facts

Grid area

Density

Decision value

Assessment

Этап 5. Найди composition defects

Проверь:

панели, которые дублируют данные или action;

панели без ясного operator question;

отсутствующие панели, без которых workflow обрывается;

неверный panel type для задачи;

слишком широкие scalar stats;

слишком узкие tables и legends;

chart panels с недостаточной высотой;

чрезмерно высокие text panels;

несогласованные widths в одной смысловой группе;

«лесенки» и случайные размеры;

orphan panels;

неравномерный vertical rhythm;

rows с одной малозначимой панелью;

дублированные drilldowns;

отсутствие escalation path;

слишком много CTAs;

first action, не связанный с текущим статусом;

navigation links, дублирующие top-level bus.

Этап 6. Предложи минимальный рефакторинг

Для каждой проблемы назначь действие:

KEEP;

RESIZE;

MOVE_WITHIN_ROW;

MOVE_BELOW_FOLD;

PROMOTE_ABOVE_FOLD;

MERGE;

SPLIT;

CHANGE_PANEL_TYPE;

CONVERT_TO_DRILLDOWN;

REMOVE_DUPLICATE;

ADD_MISSING_CONTEXT;

ADD_MISSING_ACTION;

RESTRUCTURE_ROW.

Не предлагай удаление только из-за низкой density. Для MERGE, SPLIT и REMOVE_DUPLICATE докажи, что operator facts сохраняются.

Для dashboard с P1 layout defect подготовь ASCII wireframe целевого first viewport. В wireframe укажи:

reading order;

panel roles;

grid widths;

approximate heights;

что остается above the fold;

что переносится ниже fold;

куда ведут drilldowns.

Формат результата

Dashboard Purpose Matrix.

Panel Role Inventory.

First-screen Audit.

Row/Group Density Tables для каждого dashboard.

Confirmed Layout Findings:

ID

Dashboard UID

Panel/row

Defect

Evidence

Operator impact

Severity

Confidence

Minimal refactor

Acceptance criterion

Duplicate and Missing Surface Matrix.

Target First-screen Wireframes для P1 findings.

Unverified assumptions.

Критерии качества

Каждое перемещение связано с улучшением reading order или operator workflow.

Каждое удаление сохраняет все уникальные facts и actions.

First-screen предложения проверены минимум на 1366x768 и 1920x1080.

Не предлагается новый dashboard без отдельного operator workflow.

Не предлагается менять domain/application архитектуру ради косметического layout fix.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`

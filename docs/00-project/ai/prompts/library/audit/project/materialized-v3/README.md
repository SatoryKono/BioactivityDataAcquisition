# Materialized v3 — 24 циклических промпта + Master Orchestrator

Источник: `C:/Users/Fedor/Desktop/bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx`
Дата генерации: 28.08.2026 | ID документа: BIOETL-PROMPT-ARCH-KERNEL-V3-003
Repository baseline: `main @ 3aba8559a58038cd9ff9a90621f19ea39b930a2f`
Профиль материализации: `MODE=full`, `ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true` (fail-closed kernel + explicit full-write profile)

> Полные self-contained тексты — front matter + includes сведены в один copy-paste-ready текст. Источник: `docs/00-project/ai/prompts/library/audit/` на baseline-коммите.

## Состав

| № | Объект | Prompt ID | Файл | Source path* | Score |
|---|---|---|---|---|---|
| 01 | Документация | `prompt.audit.cycle.docs` | [01-docs__prompt.audit.cycle.docs.md](01-docs__prompt.audit.cycle.docs.md) | `cycle/docs.md` | 8.87 |
| 02 | Диаграммы | `prompt.audit.cycle.diagrams` | [02-diagrams__prompt.audit.cycle.diagrams.md](02-diagrams__prompt.audit.cycle.diagrams.md) | `cycle/diagrams.md` | 8.77 |
| 03 | Агенты и память | `prompt.audit.cycle.agents-memory` | [03-agents-memory__prompt.audit.cycle.agents-memory.md](03-agents-memory__prompt.audit.cycle.agents-memory.md) | `cycle/agents-memory.md` | 8.81 |
| 04 | Конфигурация | `prompt.audit.cycle.configs` | [04-configs__prompt.audit.cycle.configs.md](04-configs__prompt.audit.cycle.configs.md) | `cycle/configs.md` | 8.73 |
| 05 | Тестовая система | `prompt.audit.cycle.tests` | [05-tests__prompt.audit.cycle.tests.md](05-tests__prompt.audit.cycle.tests.md) | `cycle/tests.md` | 8.79 |
| 06 | Технический долг | `prompt.audit.cycle.tech-debt` | [06-tech-debt__prompt.audit.cycle.tech-debt.md](06-tech-debt__prompt.audit.cycle.tech-debt.md) | `cycle/tech-debt.md` | 8.76 |
| 07 | Архитектура | `prompt.audit.cycle.architecture` | [07-architecture__prompt.audit.cycle.architecture.md](07-architecture__prompt.audit.cycle.architecture.md) | `cycle/architecture.md` | 9.12 |
| 08 | Телеметрия | `prompt.audit.cycle.telemetry` | [08-telemetry__prompt.audit.cycle.telemetry.md](08-telemetry__prompt.audit.cycle.telemetry.md) | `cycle/telemetry.md` | 8.84 |
| 09 | Дашборды | `prompt.audit.cycle.dashboards` | [09-dashboards__prompt.audit.cycle.dashboards.md](09-dashboards__prompt.audit.cycle.dashboards.md) | `cycle/dashboards.md` | 8.98 |
| 10 | Полный проект + CodeRabbit | `prompt.audit.cycle.coderabbit` | [10-coderabbit__prompt.audit.cycle.coderabbit.md](10-coderabbit__prompt.audit.cycle.coderabbit.md) | `cycle/coderabbit.md` | 9.23 |
| 11 | Medallion / write-path | `prompt.audit.project.new2.medallion` | [11-medallion__prompt.audit.project.new2.medallion.md](11-medallion__prompt.audit.project.new2.medallion.md) | `project/new2/01-medallion.md` | 8.68 |
| 12 | DQ / Pandera / Gold-контракты | `prompt.audit.project.new2.dq-contracts` | [12-dq-contracts__prompt.audit.project.new2.dq-contracts.md](12-dq-contracts__prompt.audit.project.new2.dq-contracts.md) | `project/new2/02-dq-contracts.md` | 8.64 |
| 13 | Control plane / replay / resume | `prompt.audit.project.new2.control-plane` | [13-control-plane__prompt.audit.project.new2.control-plane.md](13-control-plane__prompt.audit.project.new2.control-plane.md) | `project/new2/03-control-plane.md` | 8.68 |
| 14 | Провайдеры и каталог сущностей | `prompt.audit.project.new2.providers` | [14-providers__prompt.audit.project.new2.providers.md](14-providers__prompt.audit.project.new2.providers.md) | `project/new2/04-providers.md` | 8.45 |
| 15 | HTTP-клиенты и адаптеры | `prompt.audit.project.new2.http-clients` | [15-http-clients__prompt.audit.project.new2.http-clients.md](15-http-clients__prompt.audit.project.new2.http-clients.md) | `project/new2/05-http-clients.md` | 8.60 |
| 16 | Нормализация и идентификаторы | `prompt.audit.project.new2.normalization` | [16-normalization__prompt.audit.project.new2.normalization.md](16-normalization__prompt.audit.project.new2.normalization.md) | `project/new2/06-normalization.md` | 8.46 |
| 17 | CLI / HTTP public compatibility | `prompt.audit.project.new2.cli-compat` | [17-cli-compat__prompt.audit.project.new2.cli-compat.md](17-cli-compat__prompt.audit.project.new2.cli-compat.md) | `project/new2/07-cli-compat.md` | 8.41 |
| 18 | Безопасность и секреты | `prompt.audit.project.new2.security-secrets` | [18-security-secrets__prompt.audit.project.new2.security-secrets.md](18-security-secrets__prompt.audit.project.new2.security-secrets.md) | `project/new2/08-security-secrets.md` | 8.63 |
| 19 | VCR / HTTP fixtures | `prompt.audit.project.new2.vcr-http` | [19-vcr-http__prompt.audit.project.new2.vcr-http.md](19-vcr-http__prompt.audit.project.new2.vcr-http.md) | `project/new2/09-vcr-http.md` | 8.60 |
| 20 | QA gates и scorecard freshness | `prompt.audit.project.new2.qa-gates` | [20-qa-gates__prompt.audit.project.new2.qa-gates.md](20-qa-gates__prompt.audit.project.new2.qa-gates.md) | `project/new2/10-qa-gates.md` | 8.66 |
| 21 | GitHub Actions | `prompt.audit.project.new2.github-actions` | [21-github-actions__prompt.audit.project.new2.github-actions.md](21-github-actions__prompt.audit.project.new2.github-actions.md) | `project/new2/11-github-actions.md` | 8.57 |
| 22 | REQ-* traceability | `prompt.audit.project.new2.requirements-trace` | [22-requirements-trace__prompt.audit.project.new2.requirements-trace.md](22-requirements-trace__prompt.audit.project.new2.requirements-trace.md) | `project/new2/12-requirements-trace.md` | 8.60 |
| 23 | Operations / runbooks | `prompt.audit.project.new2.ops-runbooks` | [23-ops-runbooks__prompt.audit.project.new2.ops-runbooks.md](23-ops-runbooks__prompt.audit.project.new2.ops-runbooks.md) | `project/new2/13-ops-runbooks.md` | 8.45 |
| 24 | Scripts inventory / lifecycle | `prompt.audit.project.new2.scripts-inventory` | [24-scripts-inventory__prompt.audit.project.new2.scripts-inventory.md](24-scripts-inventory__prompt.audit.project.new2.scripts-inventory.md) | `project/new2/14-scripts-inventory.md` | 8.59 |

**Master orchestrator:** [`master-orchestrator-v1__full-project-audit.md`](master-orchestrator-v1__full-project-audit.md) — последовательный запуск всех 24 циклов (01→24 + POST_AUDIT).

## Как использовать

1. Один домен: вставь соответствующий `NN-*__prompt.*.md` как operator-paste.
2. Полный прогон 24: вставь `master-orchestrator-v1__full-project-audit.md`. Он резолвит 24 prompt_id из registry, рендерит с `MODE=full` и `ALLOW_*=true`, ведёт `master-ledger.jsonl`.
3. Baseline: `main @ 3aba8559` — сверяй drift перед стартом.

## Примечание

- Файлы — материализации на 28.08.2026. Source of truth — карточки в `library/audit/cycle/` и `library/audit/project/new2/`. Не редактируй materialized-файлы вручную; они — снапшот.
- Профиль `MODE=full, ALLOW_*=true` — explicit operator override, не library default (kernel остаётся fail-closed).
- Артефакты циклов: `reports/audit-runs/<run_id>/` — см. каждый промпт раздел Outputs.
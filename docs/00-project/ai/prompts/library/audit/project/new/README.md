______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-27'

______________________________________________________________________

# Improved cyclic pack (`prompt.audit.project.new.*`)

Десять operator-paste карточек: те же объекты, что у
[`prompt.audit.cycle.*`](../../cycle/README.md), с `ALLOW_*=true`,
ранним STOP (нет новых issue **и** нет open cycle-issue) и обязательным
`requirement_id`. Не runtime SSOT и **пока не заменяют** `library/audit/cycle/`.

Render:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.project.new.docs `
  --param N=10 --param MODE=full --param LANGUAGE=ru
```

| # | Id | File | Объект | Цель ≥8.5 |
| --- | --- | --- | --- | ---: |
| 1 | `prompt.audit.project.new.docs` | [docs.md](docs.md) | Документация + `scripts/docs` | 8.9 |
| 2 | `prompt.audit.project.new.diagrams` | [diagrams.md](diagrams.md) | Диаграммы + `scripts/diagrams` | 8.8 |
| 3 | `prompt.audit.project.new.agents-memory` | [agents-memory.md](agents-memory.md) | Агенты, skills, память | 9.0 |
| 4 | `prompt.audit.project.new.configs` | [configs.md](configs.md) | Конфиги и схемы | 9.0 |
| 5 | `prompt.audit.project.new.tests` | [tests.md](tests.md) | Тестовый слой + LANE retest | 8.9 |
| 6 | `prompt.audit.project.new.tech-debt` | [tech-debt.md](tech-debt.md) | Техдолг / residual | 8.9 |
| 7 | `prompt.audit.project.new.architecture` | [architecture.md](architecture.md) | Архитектура, 10 категорий | 9.1 |
| 8 | `prompt.audit.project.new.telemetry` | [telemetry.md](telemetry.md) | Observability data-plane | 9.0 |
| 9 | `prompt.audit.project.new.dashboards` | [dashboards.md](dashboards.md) | Presentation / DASH-* | 9.2 |
| 10 | `prompt.audit.project.new.coderabbit` | [coderabbit.md](coderabbit.md) | Проект + CodeRabbit dual-pass | 9.0 |

Порядок прогона: 1→10. `#8` перед `#9`. `#10` после доменов 1–9.

Оценки — экспертный интеграл по 10 критериям Prompt Library (SSOT, scope,
guardrails, цикл, evidence, method/skill, mutation loop, stop, composability,
dual-pass). Карточки не объявляют эти баллы в paste-теле.

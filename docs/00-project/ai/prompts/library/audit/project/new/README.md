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

Файлы пронумерованы `NN-*` по **важности для BioETL** (не по порядку
`cycle/`). Критерий: конституция `RULES.md` (§1 архитектура → конфиги/схемы
как SSOT → тесты → запрет роста техдолга → документация) плюс AI-runtime
этого репозитория, затем observability (data-plane раньше presentation),
замыкающий dual-pass.

Render (id не менялся):

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.project.new.architecture `
  --param N=10 --param MODE=full --param LANGUAGE=ru
```

| NN | Id | File | Объект | Зачем выше |
| --- | --- | --- | --- | --- |
| 01 | `prompt.audit.project.new.architecture` | [01-architecture.md](01-architecture.md) | Архитектура, 10 категорий | `RULES` §1, hexagonal / слои |
| 02 | `prompt.audit.project.new.configs` | [02-configs.md](02-configs.md) | Конфиги и схемы | YAML / Pandera — SSOT пайплайнов |
| 03 | `prompt.audit.project.new.tests` | [03-tests.md](03-tests.md) | Тестовый слой + LANE retest | `RULES` §4.2, CI-гейты |
| 04 | `prompt.audit.project.new.tech-debt` | [04-tech-debt.md](04-tech-debt.md) | Техдолг / residual | бюджеты только вниз |
| 05 | `prompt.audit.project.new.docs` | [05-docs.md](05-docs.md) | Документация + `scripts/docs` | `RULES` §6, контракт оператора |
| 06 | `prompt.audit.project.new.agents-memory` | [06-agents-memory.md](06-agents-memory.md) | Агенты, skills, память | AI-runtime репозитория |
| 07 | `prompt.audit.project.new.telemetry` | [07-telemetry.md](07-telemetry.md) | Observability data-plane | `RULES` §3.2, корм дашбордов |
| 08 | `prompt.audit.project.new.dashboards` | [08-dashboards.md](08-dashboards.md) | Presentation / DASH-* | ADR-010 optional UI |
| 09 | `prompt.audit.project.new.diagrams` | [09-diagrams.md](09-diagrams.md) | Диаграммы + `scripts/diagrams` | ADR-040, не runtime |
| 10 | `prompt.audit.project.new.coderabbit` | [10-coderabbit.md](10-coderabbit.md) | Проект + CodeRabbit dual-pass | не SSOT; после доменов 01–09 |

Порядок прогона: **01→10**. `#07` перед `#08`. `#10` после доменов 01–09.

Id карточек (`prompt.audit.project.new.<domain>`) не менялись.

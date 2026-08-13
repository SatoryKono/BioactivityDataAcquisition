______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-13'

______________________________________________________________________

# Cyclic audit pack (10 domains)

Десять полных operator-paste карточек для циклического аудита BioETL.
Не runtime SSOT. Precedence: `.codex/**` ≡ `.junie/**` → `AGENTS.md` →
`NORMATIVE_SOURCES.md` → эта папка.

Render:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.cycle.docs `
  --param N=10 --param MODE=full --param LANGUAGE=ru
```

| # | Id | File | Domain |
| --- | --- | --- | --- |
| 1 | `prompt.audit.cycle.docs` | [docs.md](docs.md) | Документация + `scripts/docs` |
| 2 | `prompt.audit.cycle.diagrams` | [diagrams.md](diagrams.md) | Диаграммы + `scripts/diagrams` |
| 3 | `prompt.audit.cycle.agents-memory` | [agents-memory.md](agents-memory.md) | Агенты, skills, память |
| 4 | `prompt.audit.cycle.configs` | [configs.md](configs.md) | Конфиг-файлы и схемы |
| 5 | `prompt.audit.cycle.tests` | [tests.md](tests.md) | Тестовый слой |
| 6 | `prompt.audit.cycle.tech-debt` | [tech-debt.md](tech-debt.md) | Технический долг |
| 7 | `prompt.audit.cycle.architecture` | [architecture.md](architecture.md) | Общая архитектура |
| 8 | `prompt.audit.cycle.telemetry` | [telemetry.md](telemetry.md) | Наблюдаемость / наполнение дашбордов |
| 9 | `prompt.audit.cycle.dashboards` | [dashboards.md](dashboards.md) | Рендер и дизайн панелей |
| 10 | `prompt.audit.cycle.coderabbit` | [coderabbit.md](coderabbit.md) | Полный аудит + CodeRabbit |

Порядок прогона: 1→10. `#8` перед `#9`. `#10` замыкает dual-pass.

Смежные one-shot / старые циклы остаются в `library/audit/`,
`library/architecture/`, `library/observability/`. Эта папка — канонический
набор из 10 полных циклических текстов.

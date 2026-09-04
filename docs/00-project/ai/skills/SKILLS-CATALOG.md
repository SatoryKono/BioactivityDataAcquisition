# Каталог Локальных Skills (Ядро BioETL)

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-07-10 (Codex skills refactor and metadata gates)*

Сводный реестр локальных BioETL-skills.

## Surface Model

- **Canonical runtime source**: `.codex/skills/`
- **Published mirror**: `docs/00-project/ai/skills/local/`
- **Curated snapshot**: `docs/00-project/ai/skills/global/`
- **Reference mirror (generated)**: `docs/00-project/ai/skills/_references/` — not canonical

## Канонические Правила

- `.codex/skills/` — канонический источник runtime skills для текущего Codex workflow.
- `docs/00-project/ai/skills/local/` — опубликованное docs-mirror/compatibility layer; его нельзя считать основным authoring source.
- `docs/00-project/ai/skills/global/` — курируемый snapshot выбранных глобальных skills.
- `docs/00-project/ai/skills/_references/` — **generated/reference mirror** of skill `references/` bundles (not authoring SoT; regenerate via `bash scripts/ai/codex/check_skills_mirror.sh --sync`).
- Frontmatter (`name`, `description`) в каждом `SKILL.md` считается контрактом триггера.

## Группы Skills

### Оркестрация

Live Codex tree does **not** ship dedicated orchestration skills. Hierarchical
review and test campaigns are modes of `py-audit-bot` (`review`) and
`py-test-bot`. Historical names `py-review-orchestrator` and `py-test-swarm`
are retired.

### Профильные Skills (live `.codex/skills/`)

| Skill | Назначение |
| --- | --- |
| `py-audit-bot` | baseline, final, targeted, review, debt, reproducibility |
| `py-config-bot` | configuration, schema, contract |
| `py-debug-bot` | reproduce, isolate, remediation guidance (read-only) |
| `py-doc-bot` | focused docs, broad docs audit, mirror sync |
| `py-plan-bot` | implementation, refactor, release planning |
| `py-test-bot` | focused tests, broad campaign, flake triage |
| `py-code-bot` | Deprecated compatibility marker only |

Retired profile names (`py-architecture-debt-bot`, `py-reproducibility-audit`)
are modes of `py-audit-bot`, not standalone skills.

### Архитектура и Качество

| Skill                   | Назначение                                 |
| ----------------------- | ------------------------------------------ |
| `architecture-guardian` | Проверка архитектурных границ              |
| `verify-architecture`   | Быстрые/полные архитектурные проверки      |
| `vcr-record`            | Запись и безопасная поддержка VCR cassette |

### Observability

Live skills are `observability-dashboard` and `observability-prometheus`.
Retired names `grafana-dashboard-extension` / `grafana-dashboard-render` and
the split `prometheus-*` skills must not be treated as current routes.

| Skill | Назначение |
| --- | --- |
| `observability-dashboard` | dashboard edit, render, query debug |
| `observability-prometheus` | rule edit, rule test, query debug |

### Документация

| Skill                         | Назначение                             |
| ----------------------------- | -------------------------------------- |
| `documentation-audit`         | Полный аудит и обновление документации |
| `documentation-cascade-audit` | Иерархический аудит документации       |

### Утилиты

| Skill                  | Назначение                                                 |
| ---------------------- | ---------------------------------------------------------- |
| `capability-discovery` | Обнаружение доступных agents/skills/quality commands       |
| `collecting-evidence`  | Создание traceable evidence objects                         |
| `deep-research`        | Структурированный deep research workflow                   |
| `synthesizing-pillars` | Синтез evidence pillars в insights и contradictions         |
| `making-decisions`     | Превращение синтеза в явные DEC-* decisions                 |
| `generating-constrained-specs` | Генерация PRD/architecture specs из decisions       |
| `initializing-ledger`  | Инициализация evidence/decision workspace                   |
| `nci-analysis`         | Анализ манипулятивных и пропагандистских паттернов          |
| `repo-config`          | Получение динамической конфигурации репозитория            |
| `suggest-users`        | Подбор reviewers/assignees на основе контекста репозитория |
| `create-pr`            | Гайд по workflow создания PR                               |

### Разработка и Дизайн

| Skill                        | Назначение                                  |
| ---------------------------- | ------------------------------------------- |
| `new-pipeline`               | Создание provider/entity pipeline           |
| `technical-designer-mermaid` | Проектирование технических Mermaid-диаграмм |

## Skill Refactor Status (2026-07-10)

- `documentation-cascade-audit` promoted to project-local Codex runtime source.
- Thin `py-*` and maintenance wrappers use a shared wrapper contract for scope,
  expected output, validation, and fallback behavior.
- Long-form generic skills use concise entrypoints with progressive disclosure
  references.
- Evidence, synthesis, decision, and constrained-spec skills share one
  evidence/decision workflow contract.
- Grafana and Prometheus skills share one prerequisites contract for runtime
  discovery, datasource checks, and no-data semantics.
- Active project skills are expected to provide `agents/openai.yaml` metadata
  and pass the Codex skill architecture gate.

## Индекс Зеркала Документации

Только **существующие** published mirrors. Runtime source of truth: `.codex/skills/`.
Skills listed in tables above but without a docs mirror live only in the Codex runtime tree.

### Local published mirrors

- [new-pipeline](local/new-pipeline/SKILL.md)
- [observability-dashboard](local/observability-dashboard/SKILL.md)
- [observability-prometheus](local/observability-prometheus/SKILL.md)
- [py-audit-bot](local/py-audit-bot/SKILL.md)
- [py-config-bot](local/py-config-bot/SKILL.md)
- [py-debug-bot](local/py-debug-bot/SKILL.md)
- [py-doc-bot](local/py-doc-bot/SKILL.md)
- [py-plan-bot](local/py-plan-bot/SKILL.md)
- [py-test-bot](local/py-test-bot/SKILL.md)
- [research-workflow](local/research-workflow/SKILL.md)
- [technical-designer-mermaid](local/technical-designer-mermaid/SKILL.md)
- [vcr-record](local/vcr-record/SKILL.md)
- [verify-architecture](local/verify-architecture/SKILL.md)

### Remaining global curated snapshot

- [py-plan-bot](global/py-plan-bot/SKILL.md)

## Примечания

- On conflict between runtime trees and docs mirrors, prefer runtime (`.codex/skills/`).
- Missing mirrors are intentional until skill-mirror sync is run; do not invent empty SKILL.md stubs in docs/.

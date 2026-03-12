# Каталог Локальных Skills (Ядро BioETL)

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-03-12 (Wave 6 consolidation)*

Сводный реестр локальных BioETL-skills.

## Канонические Правила

- `.claude/skills/` — канонический источник runtime skills для Claude Code.
- `docs/00-project/ai/skills/local/` — сгенерированное зеркало, его нельзя редактировать вручную.
- `docs/00-project/ai/skills/global/` — курируемый snapshot выбранных глобальных skills.
- `docs/00-project/ai/skills/_references/` — канонический источник reference-бандлов для overlay в `local/`.
- Frontmatter (`name`, `description`) в каждом `SKILL.md` считается контрактом триггера.

## Группы Skills

### Оркестрация

| Skill | Назначение |
|-------|---------|
| `agent-orchestration` | Карта координации multi-agent workflow |
| `py-review-orchestrator` | Иерархическая кампания code review |
| `py-test-swarm` | Иерархический test swarm (L1/L2/L3) |

### Профильные Skills

| Skill | Назначение |
|-------|---------|
| `py-audit-bot` | Профиль аудита |
| `py-config-bot` | Профиль конфигурации |
| `py-debug-bot` | Профиль отладки |
| `py-doc-bot` | Профиль документации |
| `py-plan-bot` | Профиль планирования |
| `py-test-bot` | Профиль тестирования |

### Архитектура и Качество

| Skill | Назначение |
|-------|---------|
| `architecture-guardian` | Проверка архитектурных границ |
| `verify-architecture` | Быстрые/полные архитектурные проверки |
| `vcr-record` | Запись и безопасная поддержка VCR cassette |

### Документация

| Skill | Назначение |
|-------|---------|
| `documentation-audit` | Полный аудит и обновление документации |
| `documentation-cascade-audit` | Иерархический аудит документации |

### Утилиты

| Skill | Назначение |
|-------|---------|
| `capability-discovery` | Обнаружение доступных agents/skills/quality commands |
| `deep-research` | Структурированный deep research workflow |
| `repo-config` | Получение динамической конфигурации репозитория |
| `suggest-users` | Подбор reviewers/assignees на основе контекста репозитория |
| `create-pr` | Гайд по workflow создания PR |

### Разработка и Дизайн

| Skill | Назначение |
|-------|---------|
| `new-pipeline` | Создание provider/entity pipeline |
| `technical-designer-mermaid` | Проектирование технических Mermaid-диаграмм |

## Wave 6 Consolidation (2026-03-12)

Удалены 6 skills из `.claude/skills/` (runtime) и docs-зеркал:

| Удалён | Причина |
|--------|---------|
| `collecting-evidence` | Ledger framework — не используется в BioETL |
| `synthesizing-pillars` | Ledger framework — не используется |
| `making-decisions` | Ledger framework — не используется |
| `generating-constrained-specs` | Ledger framework — не используется |
| `initializing-ledger` | Ledger framework — не используется |
| `nci-analysis` | Propaganda analysis — нерелевантно для ETL |

Также удалены 2 OpenAI metadata файла (`*.openai.yaml`).

## Индекс Зеркала Документации

- [agent-orchestration](local/agent-orchestration/SKILL.md)
- [capability-discovery](local/capability-discovery/SKILL.md)
- [create-pr](local/create-pr/SKILL.md)
- [deep-research](local/deep-research/SKILL.md)
- [documentation-audit](local/documentation-audit/SKILL.md)
- [documentation-cascade-audit](local/documentation-cascade-audit/SKILL.md)
- [new-pipeline](local/new-pipeline/SKILL.md)
- [py-audit-bot](local/py-audit-bot/SKILL.md)
- [py-config-bot](local/py-config-bot/SKILL.md)
- [py-debug-bot](local/py-debug-bot/SKILL.md)
- [py-doc-bot](local/py-doc-bot/SKILL.md)
- [py-plan-bot](local/py-plan-bot/SKILL.md)
- [py-review-orchestrator](local/py-review-orchestrator/SKILL.md)
- [py-test-bot](local/py-test-bot/SKILL.md)
- [py-test-swarm](local/py-test-swarm/SKILL.md)
- [repo-config](local/repo-config/SKILL.md)
- [suggest-users](local/suggest-users/SKILL.md)
- [technical-designer-mermaid](local/technical-designer-mermaid/SKILL.md)
- [vcr-record](local/vcr-record/SKILL.md)
- [verify-architecture](local/verify-architecture/SKILL.md)
- [architecture-guardian (public)](local/public/architecture-guardian/SKILL.md)

## Точки Входа Глобального Snapshot

- [documentation-audit](global/documentation-audit/SKILL.md)
- [gh-address-comments](global/gh-address-comments/SKILL.md)
- [gh-fix-ci](global/gh-fix-ci/SKILL.md)
- [openai-docs](global/openai-docs/SKILL.md)

## Примечания

- `py-code-bot` исключён из active published catalog: начиная с `ORCHESTRATION.md v4.0` production-код пишет orchestrator.

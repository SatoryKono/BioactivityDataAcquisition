# Каталог Локальных Skills (Ядро BioETL)

Сводный реестр локальных BioETL-skills в `.codex/skills/`.

## Канонические Правила

- `.codex/skills/` — канонический источник репозиторных локальных skills.
- `docs/00-project/ai/skills/local/` — сгенерированное зеркало, его нельзя редактировать вручную.
- `docs/00-project/ai/skills/global/` — курируемый snapshot выбранных глобальных skills.
- `docs/00-project/ai/skills/_references/` — канонический источник reference-бандлов для overlay в `local/`.
- Плоские корневые папки вида `docs/00-project/ai/skills/<skill>/` запрещены.
- Frontmatter (`name`, `description`) в каждом `SKILL.md` считается контрактом триггера.
- Проверка и синхронизация локального зеркала:

```bash
bash scripts/check_skills_mirror.sh --check
bash scripts/check_skills_mirror.sh --sync
```

## Группы Skills

### Оркестрация

| Skill | Путь | Назначение |
|------|------|---------|
| `agent-orchestration` | `.codex/skills/agent-orchestration` | Карта координации multi-agent workflow |
| `py-review-orchestrator` | `.codex/skills/py-review-orchestrator` | Иерархическая кампания code review |
| `py-test-swarm` | `.codex/skills/py-test-swarm` | Иерархический test swarm (L1/L2/L3) |

### Профильные Skills

| Skill | Путь | Назначение |
|------|------|---------|
| `py-audit-bot` | `.codex/skills/py-audit-bot` | Профиль аудита |
| `py-code-bot` | `.codex/skills/py-code-bot` | Профиль реализации кода |
| `py-config-bot` | `.codex/skills/py-config-bot` | Профиль конфигурации |
| `py-debug-bot` | `.codex/skills/py-debug-bot` | Профиль отладки |
| `py-doc-bot` | `.codex/skills/py-doc-bot` | Профиль документации |
| `py-plan-bot` | `.codex/skills/py-plan-bot` | Профиль планирования |
| `py-test-bot` | `.codex/skills/py-test-bot` | Профиль тестирования |

### Архитектура и Качество

| Skill | Путь | Назначение |
|------|------|---------|
| `architecture-guardian` | `.codex/skills/public/architecture-guardian` | Проверка архитектурных границ |
| `verify-architecture` | `.codex/skills/verify-architecture` | Быстрые/полные архитектурные проверки |
| `vcr-record` | `.codex/skills/vcr-record` | Запись и безопасная поддержка VCR cassette |

### Документация

| Skill | Путь | Назначение |
|------|------|---------|
| `documentation-audit` | `.codex/skills/documentation-audit` | Полный аудит и обновление документации |
| `documentation-cascade-audit` | `.codex/skills/documentation-cascade-audit` | Иерархический аудит документации |

### Исследование и Планирование

| Skill | Путь | Назначение |
|------|------|---------|
| `capability-discovery` | `.codex/skills/capability-discovery` | Обнаружение доступных agents/skills/quality commands |
| `collecting-evidence` | `.codex/skills/collecting-evidence` | Формирование трассируемых evidence-объектов |
| `deep-research` | `.codex/skills/deep-research` | Структурированный deep research workflow |
| `synthesizing-pillars` | `.codex/skills/synthesizing-pillars` | Преобразование evidence в synthesis insights |
| `making-decisions` | `.codex/skills/making-decisions` | Преобразование synthesis в явные решения |
| `generating-constrained-specs` | `.codex/skills/generating-constrained-specs` | Генерация PRD/архитектурных спецификаций из решений |
| `initializing-ledger` | `.codex/skills/initializing-ledger` | Инициализация workspace для evidence/decision |
| `repo-config` | `.codex/skills/repo-config` | Получение динамической конфигурации репозитория |
| `suggest-users` | `.codex/skills/suggest-users` | Подбор reviewers/assignees на основе контекста репозитория |
| `create-pr` | `.codex/skills/create-pr` | Гайд по workflow создания PR |
| `nci-analysis` | `.codex/skills/nci-analysis` | Анализ манипулятивных/дезинформационных паттернов |

### Разработка и Дизайн

| Skill | Путь | Назначение |
|------|------|---------|
| `new-pipeline` | `.codex/skills/new-pipeline` | Создание provider/entity pipeline |
| `technical-designer-mermaid` | `.codex/skills/technical-designer-mermaid` | Проектирование технических Mermaid-диаграмм |

## Текущий Статус Консолидации

- Локальное зеркало восстановлено в `docs/00-project/ai/skills/local/` и проверяется через `scripts/check_skills_mirror.sh`.
- Глобальный snapshot восстановлен в `docs/00-project/ai/skills/global/`.
- Legacy flat-папки skills удалены (Phase-2 завершён).
- Legacy одиночные артефакты удалены (`*.openai.yaml`, `*.skill.md`).
- Guardrail: `scripts/check_ai_skills_layout.sh` принудительно проверяет канонический top-level layout.
- Guardrail: в активной документации и скриптах запрещены ссылки на legacy-зеркало skills.

## Индекс Зеркала Документации

- [agent-orchestration](local/agent-orchestration/SKILL.md)
- [capability-discovery](local/capability-discovery/SKILL.md)
- [collecting-evidence](local/collecting-evidence/SKILL.md)
- [create-pr](local/create-pr/SKILL.md)
- [deep-research](local/deep-research/SKILL.md)
- [documentation-audit](local/documentation-audit/SKILL.md)
- [documentation-cascade-audit](local/documentation-cascade-audit/SKILL.md)
- [generating-constrained-specs](local/generating-constrained-specs/SKILL.md)
- [initializing-ledger](local/initializing-ledger/SKILL.md)
- [making-decisions](local/making-decisions/SKILL.md)
- [nci-analysis](local/nci-analysis/SKILL.md)
- [new-pipeline](local/new-pipeline/SKILL.md)
- [py-audit-bot](local/py-audit-bot/SKILL.md)
- [py-code-bot](local/py-code-bot/SKILL.md)
- [py-config-bot](local/py-config-bot/SKILL.md)
- [py-debug-bot](local/py-debug-bot/SKILL.md)
- [py-doc-bot](local/py-doc-bot/SKILL.md)
- [py-plan-bot](local/py-plan-bot/SKILL.md)
- [py-review-orchestrator](local/py-review-orchestrator/SKILL.md)
- [py-test-bot](local/py-test-bot/SKILL.md)
- [py-test-swarm](local/py-test-swarm/SKILL.md)
- [repo-config](local/repo-config/SKILL.md)
- [suggest-users](local/suggest-users/SKILL.md)
- [synthesizing-pillars](local/synthesizing-pillars/SKILL.md)
- [technical-designer-mermaid](local/technical-designer-mermaid/SKILL.md)
- [vcr-record](local/vcr-record/SKILL.md)
- [verify-architecture](local/verify-architecture/SKILL.md)
- [architecture-guardian (public)](local/public/architecture-guardian/SKILL.md)

## Точки Входа Глобального Snapshot

- [documentation-audit](global/documentation-audit/SKILL.md)
- [gh-address-comments](global/gh-address-comments/SKILL.md)
- [gh-fix-ci](global/gh-fix-ci/SKILL.md)
- [openai-docs](global/openai-docs/SKILL.md)
- System skills в `global/.system/**` намеренно классифицированы как internal-generated и исключены из published nav.

## Общие Generic Skills

В `.codex/skills/` могут дополнительно присутствовать непроектные generic skills (например, discovery, decision, research helpers). Они намеренно исключены из этого core-каталога.

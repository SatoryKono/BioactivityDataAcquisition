# Каталог Локальных Skills (Ядро BioETL)

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-07-10 (Codex skills refactor and metadata gates)*

Сводный реестр локальных BioETL-skills.

## Surface Model

- **Canonical runtime source**: `.codex/skills/`
- **Published mirror**: `docs/00-project/ai/skills/local/`
- **Curated snapshot**: `docs/00-project/ai/skills/global/`
- **Reference mirror**: `docs/00-project/ai/skills/_references/`

## Канонические Правила

- `.codex/skills/` — канонический источник runtime skills для текущего Codex workflow.
- `docs/00-project/ai/skills/local/` — опубликованное docs-mirror/compatibility layer; его нельзя считать основным authoring source.
- `docs/00-project/ai/skills/global/` — курируемый snapshot выбранных глобальных skills.
- `docs/00-project/ai/skills/_references/` — канонический источник reference-бандлов для overlay в `local/`.
- Frontmatter (`name`, `description`) в каждом `SKILL.md` считается контрактом триггера.

## Группы Skills

### Оркестрация

| Skill                                 | Назначение                                                                                                                             |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `agent-orchestration`                 | Карта координации multi-agent workflow                                                                                                 |
| `hierarchical-evidence-orchestration` | Иерархическая evidence-wave orchestration: shard collection через `collecting-evidence` + shard synthesis через `synthesizing-pillars` |
| `py-review-orchestrator`              | Иерархическая кампания code review                                                                                                     |
| `py-test-swarm`                       | Иерархический test swarm (L1/L2/L3)                                                                                                    |

### Профильные Skills

| Skill           | Назначение           |
| --------------- | -------------------- |
| `py-audit-bot`  | Профиль аудита       |
| `py-architecture-debt-bot` | Полный workflow снижения архитектурного долга |
| `py-code-bot`   | Deprecated compatibility marker for historical references |
| `py-config-bot` | Профиль конфигурации |
| `py-debug-bot`  | Профиль отладки      |
| `py-doc-bot`    | Профиль документации |
| `py-plan-bot`   | Профиль планирования |
| `py-reproducibility-audit` | Аудит replay determinism и воспроизводимости |
| `py-test-bot`   | Профиль тестирования |

### Архитектура и Качество

| Skill                   | Назначение                                 |
| ----------------------- | ------------------------------------------ |
| `architecture-guardian` | Проверка архитектурных границ              |
| `verify-architecture`   | Быстрые/полные архитектурные проверки      |
| `vcr-record`            | Запись и безопасная поддержка VCR cassette |

### Observability

| Skill                          | Назначение                                                               |
| ------------------------------ | ------------------------------------------------------------------------ |
| `grafana-dashboard-extension`  | Расширение, правка и валидация shipped Grafana dashboards                |
| `grafana-dashboard-render`     | Render/preflight/audit evidence for shipped Grafana dashboards           |
| `prometheus-metric-discovery`  | Поиск реальных Prometheus metrics, labels и selector-кандидатов          |
| `prometheus-query-debugger`    | Отладка PromQL, empty-state semantics и aggregation mistakes             |
| `prometheus-alert-rule-editor` | Создание и безопасная правка Prometheus-backed alert rules               |
| `prometheus-rule-testing`      | Детерминированная проверка repo-backed Prometheus rules через `promtool` |

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

- [agent-orchestration](local/agent-orchestration/SKILL.md)
- [capability-discovery](local/capability-discovery/SKILL.md)
- [deep-research](local/deep-research/SKILL.md)
- [documentation-audit](local/documentation-audit/SKILL.md)
- [documentation-cascade-audit](local/documentation-cascade-audit/SKILL.md)
- [grafana-dashboard-extension](local/grafana-dashboard-extension/SKILL.md)
- [grafana-dashboard-render](local/grafana-dashboard-render/SKILL.md)
- [hierarchical-evidence-orchestration](local/hierarchical-evidence-orchestration/SKILL.md)
- [new-pipeline](local/new-pipeline/SKILL.md)
- [py-architecture-debt-bot](local/py-architecture-debt-bot/SKILL.md)
- [py-audit-bot](local/py-audit-bot/SKILL.md)
- [py-code-bot (deprecated compatibility marker)](global/py-code-bot/SKILL.md)
- [py-config-bot](local/py-config-bot/SKILL.md)
- [py-debug-bot](local/py-debug-bot/SKILL.md)
- [py-doc-bot](local/py-doc-bot/SKILL.md)
- [py-plan-bot](local/py-plan-bot/SKILL.md)
- [py-reproducibility-audit](local/py-reproducibility-audit/SKILL.md)
- [py-review-orchestrator](local/py-review-orchestrator/SKILL.md)
- [prometheus-alert-rule-editor](local/prometheus-alert-rule-editor/SKILL.md)
- [prometheus-metric-discovery](local/prometheus-metric-discovery/SKILL.md)
- [prometheus-query-debugger](local/prometheus-query-debugger/SKILL.md)
- [prometheus-rule-testing](local/prometheus-rule-testing/SKILL.md)
- [py-test-bot](local/py-test-bot/SKILL.md)
- [py-test-swarm](local/py-test-swarm/SKILL.md)
- [repo-config](local/repo-config/SKILL.md)
- [technical-designer-mermaid](local/technical-designer-mermaid/SKILL.md)
- [vcr-record](local/vcr-record/SKILL.md)
- [verify-architecture](local/verify-architecture/SKILL.md)
- [architecture-guardian (public)](global/public/architecture-guardian/SKILL.md)

## Точки Входа Глобального Snapshot

- [documentation-audit](global/documentation-audit/SKILL.md)
- [gh-address-comments](global/gh-address-comments/SKILL.md)
- [gh-fix-ci](global/gh-fix-ci/SKILL.md)
- [openai-docs](global/openai-docs/SKILL.md)

## Примечания

- `py-code-bot` не является частью preferred active orchestration: начиная с `ORCHESTRATION.md v4.0` production-код по умолчанию пишет orchestrator.
- Если `py-code-bot` встречается в compatibility mirrors или старых workflow notes, трактуй его как deprecated compatibility profile, а не как рекомендуемый основной шаг.
- При конфликте между runtime trees и docs mirrors приоритет у runtime source,
  а не у published mirror или snapshot.

______________________________________________________________________

Version: 2.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-31'

______________________________________________________________________

# Agent Orchestration Rules

*Статус: internal-published (Internal / Extended)*

*Версия: 2.2.0 | Pointer only — runtime SSOT is `.codex/agents/ORCHESTRATION.md`*

Компактные правила оркестрации. Этот файл — docs mirror и **не** задаёт
поведение. Канон: `.codex/agents/ORCHESTRATION.md` и `.codex/agents/CODEX-RUNTIME.md`.
Для Devin: `.devin/agents/ORCHESTRATION.md`. Не хардкодить version literals runtime
ORCHESTRATION.

______________________________________________________________________

## Доступные субагенты

При работе с проектом BioETL используй специализированных субагентов через `Agent` tool:

| `subagent_type` | Model | Назначение | Зона записи |
| --- | --- | --- | --- |
| `py-audit-bot` | inherit parent | Audit, review, debt, reproducibility | read-only |
| `py-plan-bot` | inherit parent | Планирование RF-\*, декомпозиция задач | read-only |
| `py-debug-bot` | inherit parent | RCA и remediation guidance | read-only |
| `py-test-bot` | inherit parent | Тесты (baseline/final/retest), coverage | `tests/` |
| `py-config-bot` | inherit parent | YAML configs (pipeline/DQ/filter) | `configs/` |
| `py-doc-bot` | inherit parent | Документация, ADR, CHANGELOG, диаграммы | `docs/`, docstrings |

> Production-код пишем напрямую (без отдельного субагента).

## Когда использовать субагентов

| Задача                           | Субагент                            | Пример prompt                                               |
| -------------------------------- | ----------------------------------- | ----------------------------------------------------------- |
| Проверить архитектуру перед PR   | `py-audit-bot`                      | `task_id=X, phase=final, scope=src/bioetl/application/`     |
| Спланировать рефакторинг         | `py-plan-bot`                       | `task_id=X, task_description="..."`                         |
| Запустить baseline тесты         | `py-test-bot`                       | `task_id=X, phase=baseline, rf_ids=[RF-001]`                |
| Создать pipeline config          | `py-config-bot`                     | `task_id=X, mode=create, provider=chembl, entity=mechanism` |
| Разобрать падение теста          | `py-debug-bot`                      | `task_id=X, phase=post_refactor, failing_test_report="..."` |
| Обновить docs после рефакторинга | `py-doc-bot`                        | `task_id=X, rf_ids=[RF-001, RF-002]`                        |
| Полный аудит тестового покрытия  | `py-test-bot`                     | `task_id=SWARM-001, mode=full_audit`                        |
| Полный аудит документации        | `py-doc-bot` skill | `/py-doc-bot`                              |
| Иерархический code review        | `py-audit-bot`            | `task_id=REV-001, scope=src/bioetl/`                        |

## Стандартный workflow

```
① py-audit-bot (baseline) → ② py-plan-bot → ③ py-test-bot (baseline)
   → [debug цикл если FAIL] → ④ code + config (параллельно)
   → ⑤ py-test-bot (final) → ⑥ py-doc-bot → ⑦ py-audit-bot (final)
```

## Упрощённые режимы

- **Quick-fix**: test(baseline) → fix → test(final) → doc
- **Doc-only**: py-doc-bot → py-audit-bot(targeted, docs)
- **Doc-audit**: `/py-doc-bot` или `/py-doc-bot` → py-audit-bot(targeted, docs)
- **Config-only**: audit → plan → py-config-bot → test → audit

## Slash Commands (self-contained)

Skills now inlined into commands — invoke directly via `/command-name`:

| Command                        | Когда                                                         |
| ------------------------------ | ------------------------------------------------------------- |
| `/verify-architecture`         | Pre-commit проверка архитектурного тестового набора           |
| `/architecture-guardian`       | Аудит arch boundaries                                         |
| `/new-pipeline`                | Scaffolding нового ETL pipeline                               |
| `/new-composite`               | Создание composite pipeline                                   |
| `/vcr-record`                  | Управление VCR cassettes                                      |
| `/py-doc-bot`         | Аудит документации                                            |
| `/py-doc-bot` | Каскадный аудит документации с текущим docs-audit skill stack |
| `/test-swarm`                  | Иерархическое тестирование (uses py-test-bot)               |
| `/review-orchestrator`         | Code review (uses py-audit-bot)                     |
| `/mermaid-design`              | Mermaid-диаграммы с ADR-040                                   |
| `/config-validate`             | Валидация YAML vs JSON-schemas                                |
| `/schema-parity`               | Silver↔Gold schema parity                                     |
| `/provider-health`             | Статус провайдеров                                            |
| `/release-checklist`           | Pre-release audit                                             |
| `/ci-diagnose`                 | Диагностика CI workflows                                      |
| `/migration`                   | Миграции Delta Lake                                           |
| `/dependency-audit`            | CVE, лицензии                                                 |

## Полный контекст

При старте нового чата загрузи:

1. Этот файл (загружается автоматически)
1. `docs/00-project/ai/memory/agent-memory.md` — компактный контекст проекта
1. `docs/00-project/ai/agents/agents/ORCHESTRATION.md` — при оркестрации задач

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.

# Agent Orchestration Rules

*Версия: 1.0.0 | Синхронизировано с ORCHESTRATION.md v3.0 (2026-02-08)*

Компактные правила оркестрации субагентов для Claude Code.
Полная спецификация: `.claude/agents/ORCHESTRATION.md`.
Полный memory-файл: `.ai/memory/agent-memory.md`.

---

## Доступные субагенты

При работе с проектом BioETL используй специализированных субагентов через `Task` tool:

| `subagent_type` | Model | Назначение | Зона записи |
|-----------------|-------|------------|-------------|
| `py-audit-bot` | opus | Аудит кода, arch boundaries, code review | read-only |
| `py-plan-bot` | opus | Планирование RF-*, декомпозиция задач | read-only |
| `py-test-bot` | sonnet | Тесты (baseline/final/retest), coverage | `tests/` |
| `py-config-bot` | sonnet | YAML configs (pipeline/DQ/filter) | `configs/` |
| `py-debug-bot` | opus | RCA падений тестов, исправление ошибок | `src/bioetl/`, `tests/` |
| `py-doc-bot` | sonnet | Документация, ADR, CHANGELOG, docstrings | `docs/`, docstrings |

> **py-code-bot** не зарегистрирован как subagent_type — production-код пишем напрямую.

## Когда использовать субагентов

| Задача | Субагент | Пример prompt |
|--------|----------|---------------|
| Проверить архитектуру перед PR | `py-audit-bot` | `task_id=X, phase=final, scope=src/bioetl/application/` |
| Спланировать рефакторинг | `py-plan-bot` | `task_id=X, task_description="..."` |
| Запустить baseline тесты | `py-test-bot` | `task_id=X, phase=baseline, rf_ids=[RF-001]` |
| Создать pipeline config | `py-config-bot` | `task_id=X, mode=create, provider=chembl, entity=mechanism` |
| Разобрать падение теста | `py-debug-bot` | `task_id=X, phase=post_refactor, failing_test_report="...", stack_traces="..."` |
| Обновить docs после рефакторинга | `py-doc-bot` | `task_id=X, rf_ids=[RF-001, RF-002]` |

## Стандартный workflow

```
① py-audit-bot (baseline) → ② py-plan-bot → ③ py-test-bot (baseline)
   → [debug цикл если FAIL] → ④ code + config (параллельно)
   → ⑤ py-test-bot (final) → ⑥ py-doc-bot → ⑦ py-audit-bot (final)
```

## Упрощённые режимы

- **Quick-fix**: test(baseline) → fix → test(final) → doc
- **Doc-only**: py-doc-bot → py-audit-bot(targeted, docs)
- **Config-only**: audit → plan → py-config-bot → test → audit

## Репозиторные Skills (ручное исполнение)

При необходимости прочитай спецификацию и выполни вручную:

| Skill | Файл | Когда |
|-------|------|-------|
| architecture-guardian | `.claude/skills/architecture-guardian.skill.md` | Проверка arch boundaries |
| new-pipeline | `.claude/skills/new-pipeline.md` | Scaffolding нового ETL pipeline |
| vcr-record | `.claude/skills/vcr-record.md` | Управление VCR cassettes |
| verify-architecture | `.claude/skills/verify-architecture.md` | Pre-commit проверка (43 теста) |
| documentation-audit | `.claude/skills/documentation-audit.skill.md` | Аудит документации |

## Полный контекст

При старте нового чата загрузи:
1. Этот файл (загружается автоматически)
2. `.ai/memory/agent-memory.md` — полный memory с таблицами и инструкциями
3. `.claude/PROJECT_CONTEXT.md` — компактный контекст проекта
4. `.claude/agents/ORCHESTRATION.md` — при оркестрации задач

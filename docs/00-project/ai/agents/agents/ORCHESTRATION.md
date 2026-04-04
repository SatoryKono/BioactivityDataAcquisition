---
Version: 4.2.1
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-04'
---

# ORCHESTRATION.md — Оркестрация команды subagent-ов BioETL

*Версия: 4.2.1 | Дата: 2026-04-04 | Supersedes v4.2 | Платформа: Published mirror (Codex source-of-truth)*

## 1. Обзор

Команда из **8 активных субагентов** (6 core + 2 orchestrator/swarm)
обеспечивает полный жизненный цикл задачи разработки BioETL. Для текущего
Codex workflow source-of-truth orchestration живёт в
`.codex/agents/ORCHESTRATION.md`; parallel runtime copies могут существовать в
других runtime trees для соответствующих сред. Production-код
пишется напрямую оркестратором (без отдельного `py-code-bot`).

**Запуск логического профиля в Codex runtime:**
```text
spawn_agent(
  agent_type="default",
  message="Follow .codex/agents/py-audit-bot.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/."
)
```

> Runtime mapping: см. `.codex/agents/CODEX-RUNTIME.md`. Для других runtimes
> используй их собственные runtime registries и orchestration copies.

| # | Субагент (`subagent_type` / logical profile) | Model | Роль | Артефакт |
|:-:|----------------------------|-------|------|----------|
| I | **py-audit-bot** | opus | Baseline/final аудит, code review, arch guardian, API validation | `review_py-audit-bot_{YYYYMMDD}_{HHMM}_{phase}.md` |
| II | **py-plan-bot** | opus | Планирование, декомпозиция, composite design | `review_py-plan-bot_{YYYYMMDD}_{HHMM}.md` |
| III | **py-test-bot** | sonnet | Тестирование | `review_py-test-bot_{YYYYMMDD}_{HHMM}.md` |
| IV | **py-config-bot** | sonnet | Конфигурации (pipeline, DQ, filter, composite) | `review_py-config-bot_{YYYYMMDD}_{HHMM}.md` |
| V | **py-debug-bot** | opus | Отладка падений | `review_py-debug-bot_{YYYYMMDD}_{HHMM}.md` |
| VI | **py-doc-bot** | sonnet | Документация, ADR, диаграммы (Mermaid) | `review_py-doc-bot_{YYYYMMDD}_{HHMM}.md` |
| VII | **py-test-swarm** | opus | Иерархическое тестирование (L1→L2→L3) | test reports |
| VIII | **py-review-orchestrator** | opus | Иерархический code review (S1-S8) | review reports |

### Разделение ответственности (файловые зоны)

| Субагент | Зона записи | Только чтение |
|----------|-------------|---------------|
| orchestrator (direct) | `src/bioetl/`, `tests/` | `configs/`, `docs/` |
| py-config-bot | `configs/` | `src/bioetl/`, `docs/` |
| py-doc-bot | `docs/`, docstrings | `configs/`, `tests/` |
| py-test-bot | `tests/` | `src/bioetl/`, `configs/` |
| py-debug-bot | `src/bioetl/`, `tests/` (fixes) | `configs/`, `docs/` |
| py-audit-bot | — (read-only) | всё |
| py-plan-bot | — (read-only) | всё |

---

## 2. Стандартный workflow задачи

Workflow включает в себя этапы:
1. Baseline Audit (`py-audit-bot`)
2. Initial Planning (`py-plan-bot`)
3. Baseline Testing (`py-test-bot`)
4. Implementation (Parallel tracks)
5. Final Testing (`py-test-bot`)
6. Documentation (`py-doc-bot`)
7. Final Verification (`py-audit-bot`)

---

## 4. Структура артефактов

Все отчеты субагентов сохраняются в директорию `reports/{LLM}/` с префиксом `review_{agent}_{YYYYMMDD}_{HHMM}`. 

---

## 11. Changelog (ORCHESTRATION.md)

### v4.2.1 (2026-04-04)

- **SYNC**: Published mirror re-synced with Codex source-of-truth orchestration.
- **CLARITY**: Parallel Claude/Gemini runtime copies are now described as
  runtime-specific surfaces instead of the canonical orchestration owner.
- **UPD**: Версия проекта BioETL v6.1.0.

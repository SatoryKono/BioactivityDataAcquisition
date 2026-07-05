# ORCHESTRATION.md — Оркестрация команды субагентов BioETL

> **DEPRECATED (2026-02-25):** Этот файл — устаревшая адаптированная копия для Codex/Jules.
> Published docs mirror: `docs/00-project/ai/agents/agents/ORCHESTRATION.md`
> Runtime copies:
>
> - Parallel runtime orchestration copy: runtime-specific orchestration registry
> - Codex: `.codex/agents/ORCHESTRATION.md`
>   При расхождении приоритет у published mirror и runtime-реестров; этот файл сохраняется только как legacy alias.
>
> **Historical note:** дальнейшее содержимое ниже сохранено как архивный снимок ранней orchestration-модели и может содержать устаревшие роли вроде `pyCodeBot` и `pyDiagramBot`. Для текущего процесса использовать только published mirror / runtime copies выше.

*Версия: 3.1 (Adapted) | Дата: 2026-02-24 | Под проект BioETL v6.0.0*

## 1. Обзор

Для выполнения задач в проекте BioETL используется команда из **8 субагентов** (7 core + 1 специализированный diagram агент). Основной агент (Codex/Jules) оркестрирует их работу, делегируя задачи в строго определённом порядке.

|  #   | Субагент         | Роль                                                | Артефакт                                    |
| :--: | ---------------- | --------------------------------------------------- | ------------------------------------------- |
|  I   | **pyAuditBot**   | Baseline/final аудит (Hexagonal, Medallion, ADR)    | `00-audit-baseline.md`, `07-audit-final.md` |
|  II  | **pyPlanBot**    | Планирование, декомпозиция (RF-id)                  | `01-plan-initial.md`, `03-plan-updated.md`  |
| III  | **pyTestBot**    | Тестирование (pytest, VCR, coverage)                | `02-test-baseline.md`, `05-test-final.md`   |
|  IV  | **pyCodeBot**    | Production-код (Domain, App, Infra, Composition)    | `04-refactoring-log.md`                     |
|  V   | **pyConfigBot**  | Конфигурации (pipeline, DQ, filter, composite)      | `04a-config-log.md`                         |
|  VI  | **pyDebugBot**   | Отладка (DBG-id)                                    | `04-refactoring-log.md` (debug-секции)      |
| VII  | **pyDocBot**     | Документация (Johnny.Decimal, docstrings)           | `06-doc-update-log.md`                      |
| VIII | **pyDiagramBot** | Mermaid diagrams, render pipeline, docx/pdf bundles | `06-doc-update-log.md` (diagram sections)   |

______________________________________________________________________

## 2. Стандартный workflow задачи

Workflow следует принципу "Safe-by-Design":

1. **Audit (Baseline)**: Поиск текущих нарушений в `src/` и `configs/`.
1. **Plan**: Формирование списка `RF-*` изменений.
1. **Test (Baseline)**: Проверка текущего состояния тестов (`make test`).
1. **Implementation**: Параллельная работа `pyCodeBot` (код) и `pyConfigBot` (конфиги).
1. **Test (Final)**: Верификация изменений тестами и линтерами (`make lint && make test`).
1. **Documentation**: Обновление `docs/` и докстрингов.
1. **Audit (Final)**: Финальный гейткипер перед завершением задачи.

______________________________________________________________________

## 3. Инструментарий верификации (BioETL Stack)

Субагенты ОБЯЗАНЫ использовать следующие инструменты:

- **Зависимости**: `uv run python -m ...` в CI/одиночном checkout; в mixed Windows + WSL checkout используй `.\.venv-win\Scripts\python.exe -m ...` для PowerShell или `"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m ...` для WSL.
- **Линтинг**: `make lint` (ruff + mypy).
- **Тесты**: `make test-unit`, `make test-integration` (VCR).
- **Архитектура**: `pytest tests/architecture/`.
- **Конфиги**: `python docs/00-project/ai/agents/scripts/py-config-bot-2.py`, `python docs/00-project/ai/agents/scripts/py-config-bot-1.py`.
- **Терминология**: `python docs/00-project/ai/agents/scripts/py-team-orchestration.py`.

______________________________________________________________________

## 4. Expected outputs (BioETL v6.0.0)

Для новых задач отчёты сохраняются в `reports/<task-id>/`.

```
reports/<task-id>/
├── 00-audit-baseline.md
├── 01-plan-initial.md
├── 02-test-baseline.md
├── 03-plan-updated.md
├── 04-implementation-log.md
├── 04a-config-log.md
├── 05-test-final.md
├── 06-doc-update-log.md
└── 07-audit-final.md
```

______________________________________________________________________

## 5. Системы идентификаторов (IDs)

- `RF-NNN`: Изменение в коде/конфиге (Request for change).
- `DBG-NNN`: Итерация отладки.
- `AUD-NNN`: Нарушение, найденное аудитом.
- `DOC-NNN`: Изменение в документации.
- `CFG-NNN`: Изменение в конфигурационных файлах.

______________________________________________________________________

## 6. Гарантии BioETL

1. **Traceability**: Каждое изменение привязано к ID.
1. **No Blind Changes**: Сначала `Plan`, потом `Implement`.
1. **Architecture Gate**: Финальный аудит обязателен.
1. **Config Compliance**: `py-config-bot-1.py` должен иметь 0 критических замечаний.
1. **Zone Isolation**: Код в `src/`, конфиги в `configs/`, доки в `docs/`.

______________________________________________________________________

## 7. Compatibility notes

- Исторические отчёты в `docs/99-archive/reports/<task-id>/` могут использовать старые имена файлов (например, `04-refactoring-log.md` вместо `04-implementation-log.md`) и старую нумерацию ADR.
- Такие артефакты считаются **валидными историческими данными** и НЕ являются ошибкой, если сохранён контекст задачи и трассируемость ID (`AUD-*`, `RF-*`, `DBG-*`, `DOC-*`, `CFG-*`).
- Для новых задач MUST использовать текущую структуру `reports/<task-id>/` и актуальный контекст проекта; governance сверять по [`NORMATIVE_SOURCES.md`](../../../../NORMATIVE_SOURCES.md), [`RULES.md`](../../../../RULES.md) (read `Version:` header), [`REQUIREMENTS.md`](../../../../../01-requirements/REQUIREMENTS.md) и accepted ADRs в `docs/02-architecture/decisions/`.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.

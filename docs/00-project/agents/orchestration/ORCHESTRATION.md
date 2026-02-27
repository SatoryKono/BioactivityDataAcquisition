# ORCHESTRATION.md — Оркестрация команды субагентов BioETL

> **DEPRECATED (2026-02-25):** Этот файл — адаптированная копия для Codex/Jules.
> Каноническая версия для Claude Code: `.claude/agents/ORCHESTRATION.md` (v3.0).
> При расхождении — `.claude/agents/ORCHESTRATION.md` является SSOT.

*Версия: 3.1 (Adapted) | Дата: 2026-02-24 | Под проект BioETL v6.0.0*

## 1. Обзор

Для выполнения задач в проекте BioETL используется команда из **7 субагентов**. Основной агент (Codex/Jules) оркестрирует их работу, делегируя задачи в строго определённом порядке.

|  #  | Субагент        | Роль                                             | Артефакт                                    |
| :-: | --------------- | ------------------------------------------------ | ------------------------------------------- |
|  I  | **pyAuditBot**  | Baseline/final аудит (Hexagonal, Medallion, ADR) | `00-audit-baseline.md`, `07-audit-final.md` |
| II  | **pyPlanBot**   | Планирование, декомпозиция (RF-id)               | `01-plan-initial.md`, `03-plan-updated.md`  |
| III | **pyTestBot**   | Тестирование (pytest, VCR, coverage)             | `02-test-baseline.md`, `05-test-final.md`   |
| IV  | **pyCodeBot**   | Production-код (Domain, App, Infra, Composition) | `04-refactoring-log.md`                     |
|  V  | **pyConfigBot** | Конфигурации (pipeline, DQ, filter, composite)   | `04a-config-log.md`                         |
| VI  | **pyDebugBot**  | Отладка (DBG-id)                                 | `04-refactoring-log.md` (debug-секции)      |
| VII | **pyDocBot**    | Документация (Johnny.Decimal, docstrings)        | `06-doc-update-log.md`                      |

----------------------------------------------------------------------

## 2. Стандартный workflow задачи

Workflow следует принципу "Safe-by-Design":

1. **Audit (Baseline)**: Поиск текущих нарушений в `src/` и `configs/`.
1. **Plan**: Формирование списка `RF-*` изменений.
1. **Test (Baseline)**: Проверка текущего состояния тестов (`make test`).
1. **Implementation**: Параллельная работа `pyCodeBot` (код) и `pyConfigBot` (конфиги).
1. **Test (Final)**: Верификация изменений тестами и линтерами (`make lint && make test`).
1. **Documentation**: Обновление `docs/` и докстрингов.
1. **Audit (Final)**: Финальный гейткипер перед завершением задачи.

----------------------------------------------------------------------

## 3. Инструментарий верификации (BioETL Stack)

Субагенты ОБЯЗАНЫ использовать следующие инструменты:

- **Зависимости**: `uv run python -m ...` или `.venv\Scripts\python.exe -m ...`
- **Линтинг**: `make lint` (ruff + mypy).
- **Тесты**: `make test-unit`, `make test-integration` (VCR).
- **Архитектура**: `pytest tests/architecture/`.
- **Конфиги**: `python scripts/validate-pipeline-configs.py`, `python scripts/config-gap-analysis.py`.
- **Терминология**: `python scripts/lint-terminology.py`.

----------------------------------------------------------------------

## 4. Expected outputs (BioETL v6.0.0)

Отчеты сохраняются в `docs/99-archive/reports/<task-id>/` (согласно Johnny.Decimal).

```
docs/99-archive/reports/<task-id>/
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

----------------------------------------------------------------------

## 5. Системы идентификаторов (IDs)

- `RF-NNN`: Изменение в коде/конфиге (Request for change).
- `DBG-NNN`: Итерация отладки.
- `AUD-NNN`: Нарушение, найденное аудитом.
- `DOC-NNN`: Изменение в документации.
- `CFG-NNN`: Изменение в конфигурационных файлах.

----------------------------------------------------------------------

## 6. Гарантии BioETL

1. **Traceability**: Каждое изменение привязано к ID.
1. **No Blind Changes**: Сначала `Plan`, потом `Implement`.
1. **Architecture Gate**: Финальный аудит обязателен.
1. **Config Compliance**: `config-gap-analysis.py` должен иметь 0 критических замечаний.
1. **Zone Isolation**: Код в `src/`, конфиги в `configs/`, доки в `docs/`.

----------------------------------------------------------------------

## 7. Compatibility notes

- Исторические отчёты в `docs/99-archive/reports/<task-id>/` могут использовать старые имена файлов (например, `04-refactoring-log.md` вместо `04-implementation-log.md`) и старую нумерацию ADR.
- Такие артефакты считаются **валидными историческими данными** и НЕ являются ошибкой, если сохранён контекст задачи и трассируемость ID (`AUD-*`, `RF-*`, `DBG-*`, `DOC-*`, `CFG-*`).
- Для новых задач MUST использовать текущую структуру и актуальный контекст проекта BioETL v6.0.0, RULES.md v5.22 и ADR-001..ADR-039.

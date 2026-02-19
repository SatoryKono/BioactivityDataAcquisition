# ORCHESTRATION.md — Оркестрация команды субагентов BioETL

*Версия: 3.0 (Adapted) | Дата: 2026-02-08 | Под проект BioETL v5.9*

## 1. Обзор

Для выполнения задач в проекте BioETL используется команда из **7 субагентов**. Основной агент (Codex/Jules) оркестрирует их работу, делегируя задачи в строго определённом порядке.

| # | Субагент | Роль | Артефакт |
|:-:|----------|------|----------|
| I | **pyAuditBot** | Baseline/final аудит (Hexagonal, Medallion, ADR) | `00-audit-baseline.md`, `07-audit-final.md` |
| II | **pyPlanBot** | Планирование, декомпозиция (RF-id) | `01-plan-initial.md`, `03-plan-updated.md` |
| III | **pyTestBot** | Тестирование (pytest, VCR, coverage) | `02-test-baseline.md`, `05-test-final.md` |
| IV | **pyCodeBot** | Production-код (Domain, App, Infra, Composition) | `04-refactoring-log.md` |
| V | **pyConfigBot** | Конфигурации (pipeline, DQ, filter, composite) | `04a-config-log.md` |
| VI | **pyDebugBot** | Отладка (DBG-id) | `04-refactoring-log.md` (debug-секции) |
| VII | **pyDocBot** | Документация (Johnny.Decimal, docstrings) | `06-doc-update-log.md` |

---

## 2. Стандартный workflow задачи

Workflow следует принципу "Safe-by-Design":
1. **Audit (Baseline)**: Поиск текущих нарушений в `src/` и `configs/`.
2. **Plan**: Формирование списка `RF-*` изменений.
3. **Test (Baseline)**: Проверка текущего состояния тестов (`make test`).
4. **Implementation**: Параллельная работа `pyCodeBot` (код) и `pyConfigBot` (конфиги).
5. **Test (Final)**: Верификация изменений тестами и линтерами (`make lint && make test`).
6. **Documentation**: Обновление `docs/` и докстрингов.
7. **Audit (Final)**: Финальный гейткипер перед завершением задачи.

---

## 3. Инструментарий верификации (BioETL Stack)

Субагенты ОБЯЗАНЫ использовать следующие инструменты:

- **Зависимости**: `uv run python -m ...` или `.venv\Scripts\python.exe -m ...`
- **Линтинг**: `make lint` (ruff + mypy).
- **Тесты**: `make test-unit`, `make test-integration` (VCR).
- **Архитектура**: `pytest tests/architecture/`.
- **Конфиги**: `python scripts/validate-pipeline-configs.py`, `python scripts/config-gap-analysis.py`.
- **Терминология**: `python scripts/lint-terminology.py`.

---

## 4. Структура отчетов

Отчеты сохраняются в `docs/99-archive/reports/<task-id>/` (согласно Johnny.Decimal).

```
docs/99-archive/reports/<task-id>/
├── 00-audit-baseline.md
├── 01-plan-initial.md
├── 02-test-baseline.md
├── 04-implementation-log.md (бывший refactoring-log)
├── 04a-config-log.md
├── 05-test-final.md
├── 06-doc-update-log.md
└── 07-audit-final.md
```

---

## 5. Системы идентификаторов (IDs)

- `RF-NNN`: Изменение в коде/конфиге (Request for change).
- `DBG-NNN`: Итерация отладки.
- `AUD-NNN`: Нарушение, найденное аудитом.
- `DOC-NNN`: Изменение в документации.
- `CFG-NNN`: Изменение в конфигурационных файлах.

---

## 6. Гарантии BioETL

1. **Traceability**: Каждое изменение привязано к ID.
2. **No Blind Changes**: Сначала `Plan`, потом `Implement`.
3. **Architecture Gate**: Финальный аудит обязателен.
4. **Config Compliance**: `config-gap-analysis.py` должен иметь 0 критических замечаний.
5. **Zone Isolation**: Код в `src/`, конфиги в `configs/`, доки в `docs/`.

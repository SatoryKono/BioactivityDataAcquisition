# Русский промт: развернуть RF-006 и RF-008 в execution backlog

Источник: `docs/00-project/ai/prompts/codex/rf006-rf008-backlog-expansion.md`
Назначение: преобразовать сохранённые refactor-идеи в конкретный task breakdown.

## Промт

Ты — Codex, работающий как refactor planner для двух инициатив BioETL:

- `RF-006`
- `RF-008`

Исходный текст содержит strategy-level intent. Твоя задача — развернуть его в implementation backlog без изменения кода.

### Цель

Преобразовать оба плана в concrete, file-level задачи с verification strategy и sequencing.

### Ограничения

- Только read-only анализ.
- Сохраняй intent и non-goals из исходных планов.
- Не вводи speculative redesign, который не подтверждён репозиторием.

### Для каждого RF-пункта обязательно выдай

1. Objective
2. Non-goals
3. Предполагаемые target files/modules
4. Recommended execution order
5. Task breakdown со стабильными IDs
6. Required characterization tests
7. Required targeted unit/integration/architecture checks
8. Key risks и mitigations
9. Exit criteria

### Специальные инструкции

Для `RF-006` сфокусируйся на:

- seams у dependency coordinator
- декомпозиции runtime factory
- сохранении thin runner
- characterization coverage до движения кода

Для `RF-008` сфокусируйся на:

- восстановлении trustworthy high-level test signal как первом шаге
- истончении `run_all.py`
- удалении hidden composition из provider clients
- выравнивании паттернов OpenAlex и CrossRef без лишнего churn

### Финальный раздел

Покажи объединённый dependency-aware roadmap: какие задачи RF-006 и RF-008 можно вести параллельно, а какие должны идти строго последовательно.

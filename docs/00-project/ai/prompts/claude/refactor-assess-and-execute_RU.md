# Русский промт: оценить архитектуру и выполнить ограниченный refactor

Источник: `docs/00-project/ai/prompts/claude2/refactor-assess-and-execute.md`
Назначение: phase-focused workflow для архитектурной оценки и ограниченного исполнения.

## Промт

Ты — Claude Code, выступающий как refactor orchestrator BioETL.

Этот вариант предназначен для controlled cycle: сначала архитектурная оценка, затем ограниченное исполнение. Все выводы должны быть подтверждены репозиторием.

### Фаза 1. Архитектурный обзор

Подготовь структурированную оценку архитектуры с:

- 10 категориями оценки
- весом каждой категории, суммарно ровно `1.0`
- score по каждой категории от `1` до `10`
- итоговым weighted score
- кратким обоснованием по каждой категории

Минимально покрой:

- границы слоёв
- соответствие Ports and Adapters
- DDD и чистоту domain layer
- ясность зависимостей
- consistency структуры и naming
- надёжность тестового сигнала
- качество документационной поддержки
- корректность composition
- operational clarity
- концентрацию техдолга

### Фаза 2. План рефакторинга

Сформируй приоритизированный план, включающий:

- critical blockers
- medium-priority improvements
- low-priority cleanup

Для каждой задачи укажи:

- goal
- target files/modules
- proposed change
- risk
- mitigation
- definition of done
- validation plan

### Фаза 3. Ограниченное исполнение

Реализуй только те задачи, которые подходят под controlled fix-cycle:

- минимальный diff
- без ненужной декомпозиции
- с verification после каждого change-set

### Stop rules

Остановись, если:

- тесты регрессировали
- нарушены архитектурные границы
- задача требует неразрешённого изменения поведения
- refactor разросся на unrelated modules

### Финальный вывод

1. Архитектурный scorecard
2. Приоритизированный refactor plan
3. Выполненный subset, если он есть
4. Verification results
5. Явное решение continue/stop

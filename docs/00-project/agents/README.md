# AI Agents Context

Этот каталог содержит профильные инструкции для разных AI-ассистентов, используемых в BioETL.

## Available Agent Guides

| Agent         | File                                                             | Purpose                                                   |
| ------------- | ---------------------------------------------------------------- | --------------------------------------------------------- |
| Jules         | [AGENT.md](AGENT.md)                                             | Основной инженерный гайд и workflow выполнения задач      |
| Claude Code   | [CLAUDE.md](CLAUDE.md)                                           | Практики для Claude при работе с репозиторием             |
| Gemini        | [GEMINI.md](GEMINI.md)                                           | Профильный набор правил и ограничений для Gemini          |
| Codex         | [CODEX.md](CODEX.md)                                             | Инструкции Architecture Auditor + Implementation Engineer |
| Shared memory | [memory.md](memory.md)                                           | Краткая оперативная память по проекту                     |
| Orchestration | [orchestration/ORCHESTRATION.md](orchestration/ORCHESTRATION.md) | Порядок взаимодействия субагентов и артефакты             |

## Notes

- `RULES.md` остаётся canonical source всех RFC 2119 требований.
- При конфликте инструкций приоритет: System/Developer/User > локальные инструкции агента.
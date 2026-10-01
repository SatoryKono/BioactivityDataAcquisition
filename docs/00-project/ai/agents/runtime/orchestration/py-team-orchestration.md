# ORCHESTRATION.md — Оркестрация команды субагентов BioETL

> **DEPRECATED (2026-02-25):** Этот файл — устаревшая адаптированная копия для Codex/Jules.
> Published docs mirror: `docs/00-project/ai/agents/agents/ORCHESTRATION.md`
> Runtime copies:
>
> - Parallel runtime orchestration copy: runtime-specific orchestration registry
> - Codex: `.codex/agents/ORCHESTRATION.md`
>   При расхождении приоритет у published mirror и runtime-реестров; этот файл сохраняется только как legacy alias.
>
> **Historical note (2026-10-01):** архивное тело ниже удалено — оно описывало
> раннюю 8-агентную модель (`pyCodeBot`/`pyDiagramBot`, `py-config-bot-1.py`) и
> расходилось с действующими runtime-контрактами. Для текущего процесса
> использовать только published mirror / runtime copies выше.

*Версия: 3.1 (Adapted) | Дата: 2026-02-24 | Под проект BioETL v6.0.0*

## Актуальный процесс

Тело этого deprecated-зеркала вычищено до указателя (AUD-008, issue #11856).
Не использовать как источник процесса. Читать строго в порядке:

1. `docs/00-project/ai/agents/agents/ORCHESTRATION.md` (published mirror),
2. `.codex/agents/ORCHESTRATION.md` (Codex runtime copy),
3. `.junie/agents/JUNIE-RUNTIME.md` + `.junie/guidelines.md` (Junie equal peer),
4. `.devin/agents/DEVIN-RUNTIME.md` (Devin subordinate surface).

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.

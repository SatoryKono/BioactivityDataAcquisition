# Agents / runtime instructions audit

| Field | Value |
| --- | --- |
| `domain_id` | `agents-runtime` |
| `prompt_id` | `prompt.audit.agents-runtime` |
| `baseline` | `origin/main` @ `e1c184857e46` |
| `read_root` | `.worktrees/nine-domain-audit-9f71c6444175` |
| `scope` | `AGENTS.md`, `.codex/**`, `.junie/**`, `.devin/**`, `docs/00-project/ai/**` |
| `mode` | read-only audit |
| `surface_score` | **2** (acceptable) |
| `blocked` | **false** (no open P0) |

## Executive summary

Runtime SSOT для Codex/Junie/Devin согласован через `AGENTS.md`, равноправные
`CODEX-RUNTIME.md` / `JUNIE-RUNTIME.md` / `DEVIN-RUNTIME.md`, и автоматизированные
контракты зеркал. Codex–Junie parity и Codex–Devin–docs skills mirror проходят
проверки на baseline. Gemini не оформлен как tracked runtime (нет root
`GEMINI.md`, есть явный anti-SSOT guard в `AGENTS.md` и `docs/.../guides/GEMINI.md`).

Основные пробелы — **docs/prompts navigation** (битая ссылка в nine-domain pack
index), **устаревшие/противоречивые метаданные** в docs-mirror policy
(`agent-orchestration-rules.md`), и **упрощённые таблицы зон записи** в том же
mirror, которые уже не совпадают с runtime `ORCHESTRATION.md`. Рисков P0/P1 по
секретам, RCE или разрушительным скриптам без dry-run в scope не выявлено.

## Checks performed

| Check | Result |
| --- | --- |
| `python scripts/ai/junie/check_junie_mirror.py --check` | OK |
| `bash scripts/ops/support/skills/check_skills_mirror.sh --check` | OK |
| `python -m scripts.ai.prompts check` | OK (47 registry entries) |
| Root `GEMINI.md` / tracked `.gemini/agents/**` | absent (expected) |
| `docs/.../agents/agents/ORCHESTRATION.md` body vs `.codex/agents/ORCHESTRATION.md` | byte-identical from `# BioETL Codex orchestration` |

## Skipped / out of scope

- Live GitHub ruleset / workflow run verification (read-only static audit).
- `.github/copilot-instructions.md`, `opencode.json`, `scripts/**` outside agent discovery paths (not in SCOPE param).

## Top remediations

1. Исправить строку 5 в `generic-nine.pack.md`: карта `prompt.audit.github-actions` → `library/audit/github-actions.md`.
2. Синхронизировать `agent-orchestration-rules.md`: единая версия, актуальный `Last verified`, таблица зон записи = runtime ORCHESTRATION (workspace-write scopes).
3. Добавить в `memory/README.md` явное описание `gemini-memory.json` и убрать дубликаты в Role Memory Coverage Matrix.
4. Убрать или переформулировать «Status: active runtime source» в docs-mirror `ORCHESTRATION.md` (оставить только mirror banner).
5. Расширить `scripts.ai.prompts check` (или отдельный lint) на валидацию путей в pack index cards.

## Finding counts

| Metric | Value |
| --- | ---: |
| Findings total | 10 |
| PROVEN | 10 |
| P0 / P1 | 0 / 0 |
| P2 | 2 |
| P3 | 8 |

Machine-readable: [`findings.json`](findings.json).

# AI Workspace Setup — Audit and Normalize

<role>
Аудитор и оператор AI-workspace для BioETL.
Читай файлы, собирай evidence, применяй только безопасные fixes в AI-конфигурации.
</role>

<scope>
IN: `docs/00-project/ai/**`, `.claude/**`, `.codex/**`, `.gemini/**`, `.github/copilot-instructions.md`, `.vscode/mcp.json`
OUT: `src/bioetl/**`
</scope>

<source_of_truth>
1. Runtime `.claude/agents/`, `.codex/agents/` → override mirrors в `docs/00-project/ai/agents/agents/`
2. `docs/00-project/ai/agents/guides/` — canonical docs-layer для agent instructions
3. `.codex/skills/` — SSOT для local skills; `docs/00-project/ai/skills/` — doc mirror
4. `docs/00-project/ai/prompts/collected/` — archive-only, NOT SSOT
5. Все memory → `docs/00-project/ai/memory/`
</source_of_truth>

<phases>
## Phase 1. Inventory

Evidence-backed инвентаризация:
- Agent guides в `docs/00-project/ai/agents/guides/`
- Runtime: `.claude/`, `.codex/`, `.gemini/`, `.github/`
- Skills: `.codex/skills/`, `.claude/skills/`, `docs/00-project/ai/skills/`
- Prompts: `docs/00-project/ai/prompts/`
- Memory: `docs/00-project/ai/memory/`
- MCP config и paths

Для каждого mismatch: path, problem type, severity (critical|high|medium|low), evidence, recommended fix.

## Phase 2. Consistency Audit

Проверить:
- Memory references → `docs/00-project/ai/memory/`
- MCP config → `docs/00-project/ai/memory/mcp-memory.json`
- `guides/` содержит canonical instructions
- Local skills mirror = runtime skills
- Deprecated aliases маркированы, не masquerade как SSOT
- Root-level AI files на правильных местах
- Claude/Codex/Copilot/Gemini configs — internally consistent

## Phase 3. Safe Fixes

Разрешено: path corrections, stale references, doc mirror sync, MCP path normalization, clarification deprecated файлов.

Запрещено: перемещать Claude auto-memory, менять production code, удалять файлы без evidence obsolescence.

## Phase 4. Verification

- Memory path consistency
- MCP path consistency
- Skill mirror consistency
- Subagent memory references
- Broken references от собственных changes

## Phase 5. Report
</phases>

<output_format>
1. Inventory summary
2. Findings: `Severity | Path | Problem | Evidence | Action`
3. Changes made
4. Checks + outcomes
5. Remaining risks / manual follow-ups
</output_format>

<constraints>
- Локальные файлы — truth
- Scope tight
- Если change затрагивает runtime вне AI workspace → stop + explain
- Чётко разделяй observed facts vs inference
</constraints>

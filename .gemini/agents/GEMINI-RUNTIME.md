# GEMINI-RUNTIME.md — Runtime Map For BioETL Agents (Gemini CLI)

## Purpose

This file adapts BioETL's logical `py-*` agent profiles to the Gemini CLI runtime
available in this repository.

## Required Context

Before invoking a logical profile:

- use `AGENTS.md` as the root precedence contract
- read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- for write-capable work, follow
  `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

`docs/00-project/ai/**` remains a mirror/guidance layer and must not override
runtime behavior defined in `.gemini/**`.

## Key Rule

In Gemini CLI, logical profiles are implemented as **sub-agent tools**.
Instead of spawning an agent with a message, you call the tool directly.

## Invocation Pattern

Use the sub-agent tool corresponding to the logical profile.

Example:

```text
py-audit-bot(query="Perform baseline audit for task RF-001 in src/bioetl/application/")
```

## Available Sub-Agents (Tools)

| Tool Name                | Role             | Primary Responsibility                          |
| ------------------------ | ---------------- | ----------------------------------------------- |
| `py-audit-bot`           | Compliance Gate  | Baseline/final audit, RULES.md/ADR verification |
| `py-plan-bot`            | Architect        | Planning, decomposition, composite design       |
| `py-test-bot`            | Tester           | Unit and integration testing, VCR management    |
| `py-config-bot`          | Config Engineer  | YAML configurations in `configs/`               |
| `py-debug-bot`           | Troubleshooter   | Root cause analysis and fixing test failures    |
| `py-doc-bot`             | Technical Writer | Documentation, ADRs, Mermaid diagrams           |
| `py-test-swarm`          | QA Orchestrator  | Hierarchical testing (L1→L2→L3)                 |
| `py-review-orchestrator` | Review Lead      | Hierarchical code review (S1-S8)                |

## Ownership Rules

- **Main Agent (Gemini CLI)**: Orchestration and direct implementation in `src/bioetl/`.
- **py-config-bot**: Owns `configs/` write scope.
- **py-doc-bot**: Owns `docs/` and docstring edits.
- **py-test-bot**: Owns `tests/` and VCR fixtures.
- **py-audit-bot**: Read-only compliance checking.

## Related Files

- `.gemini/agents/ORCHESTRATION.md`
- `docs/00-project/ai/agents/README.md`
- `AGENTS.md` (Project Instructions)

# JUNIE-RUNTIME.md — Runtime Map For BioETL Agents (JetBrains Junie)

## Evaluation Metadata
- **Category:** Runtime Agentry
- **Weighted Score:** 7.99 / 10
- **Overall Rating:** High
- **Path:** .junie/agents/JUNIE-RUNTIME.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 8/10 (weight: 0.12)
- Context: 9/10 (weight: 0.10)
- Guardrails: 7/10 (weight: 0.10)
- Maintainability: 8/10 (weight: 0.08)
- Reusability: 7/10 (weight: 0.08)
- Error Handling: 6/10 (weight: 0.08)
- Validation: 7/10 (weight: 0.07)
- Documentation: 9/10 (weight: 0.07)

## Original Content

# JUNIE-RUNTIME.md — Runtime Map For BioETL Agents (JetBrains Junie)

This file is the JetBrains Junie equivalent of `.codex/agents/CODEX-RUNTIME.md`.
Junie and Codex are equal-peer tracked AI runtime trees for BioETL; runtime
behavior changes MUST be synchronized via
`scripts/ai/junie/check_junie_mirror.sh`.

## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
- `.junie/guidelines.md`

## Purpose

Map logical BioETL `py-*` profiles onto the native JetBrains Junie runtime
roles used in this repository. Content parity with
`.codex/agents/CODEX-RUNTIME.md` is enforced by
`scripts/ai/junie/check_junie_mirror.sh --check`; the two runtime maps MUST
keep identical logical mappings, only runtime-specific labels (Codex
`default`/`worker` vs Junie-native roles) MAY differ and are declared in
`scripts/ai/junie/junie-mirror-contract.json`.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=junie \
BIOETL_AI_AGENT=<active-profile-or-junie> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Recommended Mapping

Junie exposes its own role vocabulary; below is the logical → Junie mapping.
The `codex_role` column mirrors `.codex/agents/CODEX-RUNTIME.md` so parity is
inspectable.

| Logical profile           | Junie role | codex_role         |
| ------------------------- | ---------- | ------------------ |
| `py-audit-bot`            | default    | default            |
| `py-architecture-debt-bot`| default    | default            |
| `py-plan-bot`             | default    | default            |
| `py-test-bot`             | default    | default or worker  |
| `py-config-bot`           | worker     | worker             |
| `py-debug-bot`            | worker     | worker             |
| `py-doc-bot`              | worker     | worker             |
| `py-test-swarm`           | default    | default            |
| `py-review-orchestrator`  | default    | default            |

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-review-orchestrator` or `code-review` | diff inspection; no external writes |
| Investigate and fix CI | write only after root cause | GitHub CI workflow / `py-debug-bot` | failed checks plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | `create-pr` | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-architecture-debt-bot` | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only
unless the user also asks for implementation. Load the selected skill and
relevant sources/tests; do not load every ADR or the whole repository by
default.

## Risk-Based Validation

| Tier | Typical scope | Minimum checks |
| --- | --- | --- |
| V1 | docs-only | targeted links/drift and mirror sync |
| V2 | focused Python/tooling | targeted Ruff plus related unit tests |
| V3 | config/runtime contract | schema/contract checks plus related tests |
| V4 | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests |

Every closeout reports checks run, skipped checks with exact reasons/follow-up,
runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or
`worsened`). A lower tier cannot bypass an applicable architecture,
determinism, security, or technical-debt gate. `worsened` cannot be hidden by
raising a budget or exemption limit.

## Related Runtime Surfaces

- `.junie/guidelines.md` (root Junie contract)
- `.junie/agents/ORCHESTRATION.md`
- `.junie/agents/README.md`
- `.junie/skills/`
- `.codex/agents/CODEX-RUNTIME.md` (equal-peer Codex runtime map)
- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/skills/`
- `scripts/ai/junie/check_junie_mirror.sh` (parity enforcement)
- `scripts/ai/junie/junie-mirror-contract.json` (parity contract)

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.

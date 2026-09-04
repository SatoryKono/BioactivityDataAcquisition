---
id: prompt.audit.agents-runtime
version: 1.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
- AUDIT_MODE
- REQUIRE_GH_TRACKING
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
- fragments/peer-review-gate.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
- docs/00-project/ai/prompts/README.md
- .codex/agents
- .junie/agents
anti_patterns:
- Treating prompts as runtime SSOT
- Ignoring .codex/.junie/.devin discovery
- Auto-running destructive agent scripts
tags:
- audit
- agents
- runtime
- scripts
- operator
summary: Audit AI agent instructions, skills, and agent-related scripts
max_body_lines: 150
---
# Agents / runtime instructions audit

**Kit:** prompt 6 of `prompt.audit.generic-nine.pack`.
Audit repository instructions and scripts for AI coding/review agents.
Criteria: correct project context, least privilege, reproducible
bootstrap/build/test, no conflicting instructions, safe shell/tool use.
Prompts library is **operator aid only** — runtime SSOT is `.codex/**`,
`.junie/**`, `.devin/**` (+ governance stack).


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/agents/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | AI runtime + agent scripts (see discovery) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Discovery (BioETL-first)

Must include when present:

- `AGENTS.md`, `Agents.md`
- `.codex/agents/**`, `.codex/skills/**`
- `.junie/agents/**`, `.junie/skills/**`
- `.devin/agents/**`, `.devin/skills/**`, `.devin/prompts/**`
- `docs/00-project/ai/**` (mirrors/guides — not behavior SSOT alone)
- `docs/00-project/ai/prompts/**` (library)
- optional: `.github/copilot-instructions.md`, `.github/instructions/**`,
  `.github/agents/**`, `CLAUDE.md`, `GEMINI.md`
- `scripts/` matching agent/bootstrap/validate/check/review/docs

Build **instruction scope graph**: root → path-specific → agent profile →
skill → scripts → CI validation. Flag contradictions (commands, versions,
write vs read-only roles).

## Method

1. Inventory surfaces; mark owner (runtime vs docs mirror vs prompts).
2. Validate canonical build/test commands against manifests.
3. Scripts: idempotency, dry-run for destructive ops, non-zero on failure,
   no `curl|bash` / unquoted sinks / secret-on-stdout.
4. Permissions: audit/read vs deploy/write separation.
5. Mirror parity: if `.codex` or `.junie` changed in remediation path, note
   `scripts/ai/junie/check_junie_mirror.sh --check`.

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Instructions consistent; scripts reproducible; tools limited; validation automated |
| 2 | Main workflow reliable; a few undocumented preconditions |
| 1 | Implicit env assumptions, excessive permissions, or conflicting instructions |
| 0 | Agent can leak a secret, destroy data, or run uncontrolled privileged action |

P0: destructive/secret/RCE. P1: wrong build/release/deploy. P2: nondeterminism.
P3: discoverability.

## Output

- `reports/audit/agents/report.md` + `findings.json`
- kit extras: `agent-instruction-map.md`, `agent-scripts.csv`,
  `tool-permissions.csv`, `instruction-conflicts.csv`, command matrix
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Script that can leak secrets or destroy data without guard → P0. Do not
“fix” by editing runtime without mirror plan. Empty SCOPE → STOP.

## Canonical Sources

- Runtime contract and precedence: `AGENTS.md`
- Normative source index: `docs/00-project/NORMATIVE_SOURCES.md`

Load only the role- and risk-relevant sources selected by those contracts.

# BioETL Codex orchestration

Status: active runtime source. Owner: BioETL Team. Last verified: 2026-09-01.

## Authority and bootstrap

`AGENTS.md` defines repository-wide runtime behavior and precedence. Before
planning, auditing, or editing, complete its required context and memory loop.
Use `docs/00-project/NORMATIVE_SOURCES.md` to select the applicable RULES,
requirements, ADRs, and policies. This file only defines Codex routing; it does
not restate project governance.

For a role-specific task, read the matching `.codex/agents/py-*.md`, wrapper
skill, and `docs/00-project/ai/memory/memory-py-*.md`. Load additional sources
only when the task touches their governed surface.

## Governed roles

| Role | Default authority | Purpose |
| --- | --- | --- |
| `py-audit-bot` | read-only | Independent evidence and compliance audit |
| `py-config-bot` | workspace write | Config, schema, generated-config, and contract remediation |
| `py-debug-bot` | read-only | Reproduction, isolation, root cause, remediation guidance |
| `py-doc-bot` | workspace write | Canonical docs, contributor guidance, and mirror sync |
| `py-plan-bot` | read-only | Scoped, dependency-aware implementation plans |
| `py-test-bot` | workspace write | Focused tests, failure classification, regression evidence |

Native descriptors inherit the parent model. A role never expands user
authority, filesystem scope, network access, or destructive-action permission.

## Risk tiers and routing

Classify the task before loading optional context:

| Tier | Typical change | Route |
| --- | --- | --- |
| V1 | docs-only or one low-risk metadata surface | Direct root/single-agent execution |
| V2 | focused code, test, config, or tooling change | Direct root/single-agent execution; load one matching role when useful |
| V3 | cross-surface config/runtime contract, migration, or CI behavior | Explicit plan; matching specialist; targeted audit/test gates |
| V4 | architecture, security, broad refactor, release/governance change | Baseline evidence, dependency-aware plan, implementation, final tests/docs/audit |

V1/V2 do not require a subagent chain or formal report bundle unless the user,
active skill, or touched contract requires one. V3/V4 retain orchestration and
post-change validation. When delegation is unavailable or unnecessary, the
root agent performs the same responsibilities directly.

## Standard task loop

1. Resolve user intent, mutation authority, scope, and risk tier.
1. Run the canonical memory `pre-task` workflow with runtime/agent identity.
1. Inspect current evidence: target files, related tests, contracts, configs,
   docs, mirrors, and debt registries.
1. For V3/V4, maintain an explicit plan with at most one active step.
1. Make the smallest authorized change; preserve unrelated worktree changes.
1. Validate proportionately and follow
   `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` for writes.
1. Synchronize runtime/docs/generated mirrors only from their canonical owner.
   Markdown link or `Owner:` / `Status:` / `Class:` header changes require
   `python -m scripts.docs generate-cleanup-inventory --update` in the same
   changeset.
1. Run the memory `post-task` workflow and report evidence, skips, mirror
   status, and debt outcome.

Diagnosis and review remain read-only unless implementation was also requested.
`py-debug-bot` never applies fixes: it returns a reproduction, root cause,
confidence, remediation options, and exact regression checks to an authorized
write-capable parent.

## Evidence and decisions

- Prefer repository evidence and executable checks over remembered counts.
- Each blocking finding needs a location, governing source, reproducible
  evidence, severity, and remediation.
- Audit findings require two independent verification methods when feasible.
- Package or file count alone is not architecture debt; calibrate against the
  current topology/governance evidence and debt registries.
- If evidence conflicts, follow canonical precedence and record the conflict.
- Never solve a failure by increasing a debt budget, exemption cap, threshold,
  or hotspot allowance.

## Validation by risk

| Tier | Minimum closeout |
| --- | --- |
| V1 | targeted docs/link/drift check; mirror check when applicable |
| V2 | focused lint/type/test checks for touched behavior |
| V3 | schema/runtime/architecture contract checks plus focused regressions |
| V4 | applicable architecture, lint, type, security, broad test, docs, and debt gates |

A lower tier cannot bypass a gate required by the touched surface. Report every
skipped check with its reason and exact follow-up command. Changes under
Codex/Junie runtime trees must satisfy the repository mirror contract.

## MCP and external evidence

Use MCP by current capability discovery, not historical server names. Daily
readiness is the bounded, read-only `stable` profile. Optional monitoring,
Docker, graph, browser, and external services are started only when the user or
task explicitly requires them. External research supplements but never
replaces tracked contracts.

## Escalation and safety

Stop and request direction when completion requires materially broader scope,
new authority, a destructive action with unclear targets, or an `.env` change.
Do not create, edit, rename, move, overwrite, or delete `.env` files without
explicit per-task approval. Keep secret-bearing and machine-local values out of
tracked files, reports, logs, and tool output.

## Canonical references

- `AGENTS.md`
- `.codex/agents/CODEX-RUNTIME.md`
- `.codex/agents/py-*.md`
- `.codex/skills/py-*/SKILL.md`
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `src/memory/DAILY_WORKFLOW.md`

---
id: prompt.audit.generic-nine.pack
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/unknown-params.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/reports-output.md
  - fragments/generic-nine-contract.md
related_ssot:
  - docs/00-project/ai/prompts/library/audit/generic-nine/README.md
  - docs/00-project/ai/prompts/README.md
  - AGENTS.md
anti_patterns:
  - Using the archived megaprompt as default paste
  - Inventing stack, SLA, coverage, or threat-model facts
  - Mixing docs-content findings into docs-pipeline (or the reverse)
  - Writing artifacts to repo root
  - Raising technical-debt budgets
tags: [audit, pack, generic-nine, operator]
summary: Pack routing for the nine-domain generic code/project audit kit
max_body_lines: 90
---

# Generic nine-prompt audit pack

Shared contract: `fragments/generic-nine-contract.md`.
Source kit: 2026-08-11 07:12 BST. Artifacts: `reports/audit/<domain>/`.

| # | Card | Surface score meaning (3 = good) |
| --- | --- | --- |
| 1 | `prompt.audit.docs-content` | Critical scenarios described; commands checked; links automated |
| 2 | `prompt.audit.tests-system` | Critical paths covered; isolated/stable; CI actually blocks |
| 3 | `prompt.audit.tech-debt` | Debt identified with owner/risk/effort; new code does not worsen baseline |
| 4 | `prompt.audit.repo-tree` | Root minimal; generated/cache excluded; tree matches boundaries |
| 5 | `prompt.audit.github-actions` | Least privilege; pinned actions; reproducible CI; controlled deploy |
| 6 | `prompt.audit.agents-runtime` | Consistent instructions; reproducible scripts; limited tools |
| 7 | `prompt.audit.diagrams` | Text source VCS; deterministic render; model matches the system |
| 8 | `prompt.audit.docs-pipeline` | One-command clean build; pinned toolchain; links/API checked in CI |
| 9 | `prompt.architecture.review` | Boundaries clear; deps controlled; ADR/docs match code/infra |

Run one domain or 1→9. Do not invent unknown parameters. Default `MODE=audit`
(read-only). For N-iteration fix loops use `prompt.audit.orchestrator` or
`prompt.audit.cycle.*` — this pack does not open issues or apply patches.

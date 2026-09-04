---
id: prompt.audit.cycle
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- codex
- any
params:
- REPO
- BASE
- WORK_BRANCH
- SCOPE
- MODE
- CYCLE_COUNT
- AUDIT_MODE
- REQUIRE_GH_TRACKING
- LANGUAGE
- DOMAIN
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
- fragments/cyclic-kernel-v3.md
- fragments/evidence-contract-v3.md
- fragments/issue-state-machine-v3.md
- fragments/finding-schema.md
- fragments/audit-scale.md
- fragments/orchestrator-guards.md
- fragments/peer-review-gate.md
- fragments/project-requirements-audit.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- .codex/agents/py-audit-bot.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
- configs/quality/architecture_metric_exemptions.yaml
anti_patterns:
- Four parallel audit kits in one session
- Empty cycles for form
- Raising debt budgets or exemptions
- Closing issues without origin/main evidence
tags:
- audit
- cycle
- grok
- operator
summary: One audit cycle — kernel v3 plus domain overlay; successor of grok-audit-cycle
  and cyclic-pack
max_body_lines: 300
---
# BioETL audit cycle

One function: **one audit cycle** for `{{DOMAIN}}` (or `SCOPE`). Replaces four kits
(`generic-nine`, `project-new`, `cyclic-pack`, `grok-audit-cycle`).

Shared rules come from `includes:` (kernel, evidence, issue FSM, guardrails).
Do not paste RULES.md.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/<audit-slug>` (never main) |
| `SCOPE` | surface list or theme |
| `DOMAIN` | overlay key in `domains.yaml` (e.g. `docs`, `tech-debt`) |
| `MODE` | `audit` |
| `CYCLE_COUNT` | `1` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `true` |
| `LANGUAGE` | `ru` (code/ids/paths original) |

## Compile a domain card

```text
python -m scripts.ai.prompts compile --domain {{DOMAIN}} --profile audit-readonly
```

Legacy ids `prompt.audit.cycle.docs` … `prompt.audit.cycle.coderabbit` map to
`domains.yaml` keys `docs`, `diagrams`, `agents-memory`, `configs`, `tests`,
`tech-debt`, `architecture`, `telemetry`, `dashboards`, `coderabbit`.

## Architecture metric exemptions

For architecture metric **exemptions**: `python -m scripts.engineering.qa generate-debt-tasks`
reads `configs/quality/architecture_metric_exemptions.yaml` (registers
`file_size_limits`, `function_complexity`, `function_length`, `class_size`,
`class_method_count`, `god_object`, `domain_complexity`). Even an empty
register belongs in the JSON summary (`count=0`). Do not change product code
in that mode — only emit
`reports/quality/tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json`.

## Stage 0 — Scope lock

- `full`: inventory only paths that **exist** under SCOPE
- `differential`: delta vs `origin/BASE` ∩ SCOPE
- Empty SCOPE → STOP

## Stage 1 — Findings

Each finding: severity, path, claim, evidence, status `PROVEN` \| `NOT_PROVEN`.
No file-level proof → `NOT_PROVEN` (no issue).

## Stage 2 — GitHub

If `REQUIRE_GH_TRACKING=true`: search open issues before create; one root cause
per issue; API fail → `BLOCKED_GH`.

## Stage 3 — Remediation

Fix PROVEN in-scope items only. Post-change validation. Never commit to `{{BASE}}`.

## Stop

`NO_ACTIONABLE_FINDINGS` → stop. Secret risk → stop + ask.

## Cycle closeout

| Finding | Severity | Issue | State | Commit/PR | Verification |
| --- | --- | --- | --- | --- |

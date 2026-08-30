---
id: prompt.audit.project.new2.vcr-http
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - configs/quality/integration_vcr_policy.yaml
  - .codex/skills/vcr-record/SKILL.md
  - tests/fixtures/vcr/uniprot/test_uniprot_protein_metadata_fields_meta.yaml
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Secrets or tokens in cassettes
  - Non-deterministic cassette bodies
  - Recording live traffic without skill placement rules
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, vcr, http, fixtures, secrets, cycle, operator]
summary: Cyclic VCR cassette audit — placement, determinism, secret-safety, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic VCR / HTTP fixture audit

Skill: **vcr-record**. Не live HTTP-контракт адаптеров (см. http-clients).
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `tests/fixtures/vcr/ configs/quality/integration_vcr_policy.yaml` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/vcr-cycle-new2-<shortsha>` |

## Anchors

- Policy: `configs/quality/integration_vcr_policy.yaml`
- Placement/determinism/secret-safety from vcr-record skill
- Never commit tokens; redact headers/bodies
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. `run_id = <UTC>-vcr-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`. Do **not** paste cassette secrets
   into reports.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Cassette tree vs policy. Orphans / missing meta. |
| **B Secrets** | Scan for token/key patterns without echoing values into issues. |
| **C Determinism** | Unstable timestamps, unordered JSON, host leakage. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[vcr][<REQ-id>][P#]`. |
| **E Fix** | Redact/replace via skill workflow. |
| **F Validate** | Targeted VCR tests. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Secret in cassette → P0; do not copy secret into GitHub.

## Success

- Policy vs tree matrix
- No secret material in new commits or issue bodies

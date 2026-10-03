---
id: prompt.audit.reconcile
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- codex
- junie
- devin
- any
params:
- SCOPE
- LANGUAGE
- BASE_BRANCH
- REPO
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/finding-schema.md
- fragments/audit-scale.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/RULES.md
- docs/00-project/ai/prompts/library/audit/comprehensive.md
anti_patterns:
- Treating primary audit conclusions as facts
- Deleting rejected hypotheses instead of retaining reconciliation history
- Confirming a P0/P1 without reproducing its key evidence
- Re-scoring from stale or unbound generated reports
- Creating issues during reconciliation
tags:
- audit
- review
- reconciliation
- double-check
- evidence
- operator
summary: Independent P20 reconciliation for comprehensive BioETL audits
max_body_lines: 180
---
# P20 — independent audit reconciliation

Read-only final reviewer for `prompt.audit.comprehensive`. Primary findings are
hypotheses until independently checked.

## Inputs

Immutable snapshot:

- Audit Manifest and audited revision;
- Evidence Ledger;
- raw P01–P19 findings;
- root-cause clusters;
- concern ownership/coverage matrix;
- contradictions/exceptions register;
- unresolved evidence register.

Do not mutate code, GitHub Issues, PRs, budgets or source findings.

## Independence

Prefer a different reviewer/session from the primary stages.

Order:

1. inspect raw evidence before reading the primary rationale where practical;
2. attempt independent reproduction/disproof;
3. then compare with the primary conclusion.

If independent execution is technically impossible, record the limitation and
do not inflate confidence.

## Review protocol

### P0/P1

Re-open every finding's current evidence and reproduce the key check. Verify:

- audited revision binding;
- requirement/invariant source;
- attempted disproof;
- exception/suppression search;
- root-cause assignment;
- proposed remediation does not violate another invariant.

### P2

Review at least one finding from every `root_cause_id` cluster and every
audit-domain. Expand to the entire cluster on disagreement, stale evidence, or
severity uncertainty.

### P3

Perform schema, dedupe and consistency review plus risk-based substantive
sampling.

## Review verdict

Keep finding `status` as `PROVEN | NOT_PROVEN`. Add:

`review_verdict = CONFIRMED | DOWNGRADED | REJECTED | NOT_VERIFIABLE`.

Rules:

- `CONFIRMED`: current evidence reproduces and disproof/exception checks do not
  neutralize the claim.
- `DOWNGRADED`: claim is real but impact/priority/confidence was overstated.
- `REJECTED`: independent evidence falsifies the primary claim or establishes
  a valid exception.
- `NOT_VERIFIABLE`: reviewer cannot obtain sufficient current evidence.

Only `CONFIRMED` and accepted `DOWNGRADED` findings enter the canonical
actionable register.

## Reconciliation record

For every reviewed finding record:

- source finding id and fingerprint;
- `root_cause_id`;
- final finding id if retained;
- old/new priority, status, confidence and review verdict;
- reviewer Evidence IDs;
- reason code;
- disagreement/dissent note;
- exception reference when applicable.

Never delete rejected/downgraded hypotheses from the audit trail.

## Cross-prompt reconciliation

Detect:

- duplicated symptoms with one root cause;
- one symptom incorrectly merged across distinct root causes;
- severity inflation/deflation;
- stale/unbound evidence;
- invalid exception handling;
- normative contradictions;
- incompatible remediation recommendations;
- fixes that weaken validation/tests/governance;
- concern ownership gaps.

If a PRIMARY ownership gap remains, comprehensive audit is incomplete.

## Outputs

```text
reconciliation-ledger.json
canonical-findings.json
rejected-downgraded.json
final-coverage-matrix.csv
final-scorecard.json
roadmap.md
not-verifiable.json
anti-remediation.md
```

Roadmap entries require root cause, affected paths, dependencies, acceptance,
validation and rollback risk.

## Done when

- all P0/P1 independently reproduced or explicitly `NOT_VERIFIABLE`;
- P2 sampling covers every root-cause cluster/domain;
- concern matrix has no unexplained PRIMARY gap;
- canonical register contains only current evidence-backed findings;
- evidence → finding → root cause → recommendation → acceptance → validation is
  fully traceable.

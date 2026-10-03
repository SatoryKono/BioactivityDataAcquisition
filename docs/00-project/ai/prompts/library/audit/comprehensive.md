---
id: prompt.audit.comprehensive
version: 2.0.0
status: active
class: campaign
owner: BioETL Team
runtimes:
- codex
- junie
- devin
- any
params:
- SCOPE
- AUDIT_MODE
- LANGUAGE
- EXTERNAL_VERIFY
- BASE_BRANCH
- REPO
- WORK_BRANCH
- ALLOW_ISSUE_WRITE
- ALLOW_PUSH
- ALLOW_MERGE
- ALLOW_CLOSE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/finding-schema.md
- fragments/audit-scale.md
- fragments/language-ru.md
- fragments/orchestrator-guards.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/RULES.md
- docs/02-architecture/decisions/
- docs/00-project/ai/prompts/README.md
- docs/00-project/ai/prompts/domains.yaml
- docs/00-project/ai/prompts/library/audit/cycle.md
- docs/00-project/ai/prompts/library/audit/reconcile.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
- Running P01-P20 as unrelated full-repo audits with duplicated evidence
- Treating stale generated reports as current facts
- Skipping P20 independent reconciliation
- Creating one GitHub issue per symptom instead of per root cause
- Performing remediation before canonical findings are reconciled
- Raising debt or skip budgets to make findings disappear
tags:
- audit
- comprehensive
- bioetl
- dag
- evidence
- reconciliation
- operator
summary: BioETL comprehensive audit v2 — dependency-aware P00-P20 campaign over Prompt Library domains
max_body_lines: 360
---
# BioETL comprehensive audit v2 — P00→P20

This campaign integrates the audited BioETL prompt pack v2 into the current
Prompt Library. It is an operator-paste orchestration surface, not runtime SSOT.

Defaults: `AUDIT_MODE=full`, `LANGUAGE=ru`, `EXTERNAL_VERIFY=false`,
`BASE_BRANCH=main`, `REPO=SatoryKono/BioactivityDataAcquisition`, all
`ALLOW_*=false`. Audit is read-only through P20. GitHub/code mutation is
post-audit only and remains fail-closed behind the existing write profile.

## P00 — Orchestrator contract

1. Pin revision, branch, worktree state and toolchain.
2. Read active normative sources and build a `Normative Source Map`.
3. Build shared inventories once; downstream stages reuse Evidence IDs.
4. Build a Concern Ownership Matrix with exactly one PRIMARY owner per concern.
5. Execute the dependency DAG below; parallelize only independent read-only work.
6. Collect every stage handoff into one Evidence Ledger.
7. Do not assign final review verdicts before P20.

## Shared inventory

Collect once:

- package/import topology and public entrypoints;
- configs/providers/entities/pipelines/workflows/composites;
- contract/schema/normalization/DQ registries;
- tests, markers, coverage/governance artifacts with freshness;
- CI workflows/actions and package/build metadata;
- docs/ADRs/runbooks;
- manifests/ledgers/checkpoints/lineage;
- metrics/rules/dashboards/alerts;
- quality/debt/generated reports with producer revision;
- scripts/root allowlists and compatibility surfaces.

Artifacts:
`audit-manifest.json`, `evidence-ledger.json`,
`concern-ownership.csv`, `shared-inventory.json`.

## P01–P20 stage map

| Stage | PRIMARY concern | Prompt Library execution surface |
| --- | --- | --- |
| P01 | Architecture boundaries | domain `architecture` |
| P02 | DDD/domain invariants | domain `architecture`, category `ddd_invariants` |
| P03 | Application orchestration | domains `architecture` + `control-plane` |
| P04 | Infrastructure/storage/adapters | domains `medallion` + `http-clients` + `providers` |
| P05 | Interfaces/CLI/HTTP boundaries | domains `cli-compat` + `architecture` |
| P06 | Composition/DI | domain `architecture`, category `composition_di` |
| P07 | Medallion/data contracts | domains `medallion` + `dq-contracts` |
| P08 | Config/precedence/SSOT | domain `configs` |
| P09 | DQ/normalization/schema drift | domains `dq-contracts` + `normalization` |
| P10 | Composite/workflow semantics | domain `composite-workflow` |
| P11 | Reproducibility/replay | domain `reproducibility` + `control-plane` |
| P12 | External API/resilience | domains `http-clients` + `providers` + `vcr-http` |
| P13 | Tests/coverage/flakiness | domains `tests` + `qa-gates` |
| P14 | Observability/ops readiness | domains `telemetry` + `dashboards` + `ops-runbooks` |
| P15 | Performance/resources | domain `performance` |
| P16 | Security/secrets/supply chain | domains `security-secrets` + `github-actions` |
| P17 | CI/CD/release/quality gates | domains `github-actions` + `qa-gates` |
| P18 | Docs/ADR/traceability parity | domains `docs` + `diagrams` + `requirements-trace` |
| P19 | Repo hygiene/typing/dead code | domains `repo-hygiene` + `tech-debt` + `scripts-inventory` |
| P20 | Independent double-check | `prompt.audit.reconcile` |

Compile a domain card with:

```text
python -m scripts.ai.prompts compile --domain <domain> --profile audit-readonly
```

When a stage uses several domains, execute each domain once, preserve its
Evidence IDs, then produce one stage handoff. Do not re-run a full repo scan per
domain when the shared inventory already proves the same fact.

## Dependency DAG

### Wave F — foundation

Run read-only in parallel when inventories are ready:

- P01, P02, P04, P05, P06, P08, P16, P19;
- P13 baseline collection may run in parallel.

### Wave D1

- P03 after P02 + P06.
- P07 after P04 + P08.
- P12 after P04.
- P17 after P13 + P16.

### Wave D2

- P09 after P07 + P08 + P12.
- P10 after P03 + P06 + P08 + P09.

### Wave D3

- P11 after P07 + P08 + P10.
- P14 after P03 + P04 + P10 + P11 + P12.

### Wave D4

- P15 after P04 + P10 + P13 + P14.
- P18 after implementation audits P01–P17 have final stage handoffs.

### Final

- P20 after P01–P19 handoffs and coverage reconciliation.

A stage may start independent inventory work earlier, but its final finding set
must reference the latest prerequisite handoffs.

## Stage handoff contract

Every P01–P19 stage returns:

- Evidence IDs used/created;
- `findings.json` using the shared finding schema;
- `root_cause_id` clusters;
- concerns covered/not covered;
- prerequisite handoff ids;
- contradictions and valid exceptions checked;
- `NOT_PROVEN` / unresolved evidence gaps;
- output extras required by its domain overlays.

Do not copy evidence into a new anonymous format. Retain the original Evidence
ID and revision binding.

## Cross-stage rules

- One root cause may have symptoms in several stages; cluster by
  `root_cause_id`, not prompt id.
- A recommendation that violates another stage invariant is invalid.
- Missing evidence is not evidence of absence.
- Generated reports are current only when their producer/source revision is
  bound to the audited revision.
- Compatibility seams, generated files and explicit exceptions must be tested
  before declaring duplication/dead code.
- External provider/API claims remain `NOT_PROVEN` when
  `EXTERNAL_VERIFY=false` and repo evidence cannot establish the current
  external contract.

## P20 entry gate

Before reconciliation, produce:

- immutable Audit Manifest;
- Evidence Ledger;
- raw P01–P19 findings;
- root-cause clusters;
- concern ownership/coverage matrix;
- contradictions/exceptions register;
- unresolved evidence register.

If any concern has no PRIMARY owner, comprehensive audit is incomplete.

Run `prompt.audit.reconcile` as a separate reviewer/session when possible.

## Final outputs

```text
reports/audit-runs/<run_id>/comprehensive/
  audit-manifest.json
  evidence-ledger.json
  concern-ownership.csv
  stage-handoffs/
  raw-findings.json
  root-cause-clusters.json
  contradictions.json
  unresolved-evidence.json
  reconciliation-ledger.json
  canonical-findings.json
  rejected-downgraded.json
  coverage-matrix.csv
  final-scorecard.json
  final-report.md
  roadmap.md
```

## Post-audit write mapping

The original package POST-A/POST-B flows map to the existing fail-closed
`prompt.audit.orchestrator` and closeout cards:

- issue payload/create/reuse uses `root_cause_id` and finding fingerprint;
- mutation requires the full-write profile or explicit `ALLOW_*=true`;
- one Issue per root cause/atomic change set;
- fixes run on a work branch, never directly on `main`;
- after remediation rerun affected stages plus P20 reconciliation.

Do not open Issues from raw P01–P19 findings before P20.

## Done when

- P01–P19 completed or have explicit unresolved evidence records;
- every concern has one PRIMARY owner;
- P20 independently rechecked all P0/P1 and risk-sampled P2/P3;
- canonical findings are traceable evidence → finding → root cause →
  recommendation → acceptance → validation;
- no final P0/P1 depends only on stale/unbound evidence;
- post-audit mutations, if requested, remain under existing write guardrails.

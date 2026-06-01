# Technical Debt Evidence Summary

Дата: 2026-03-21
Статус: актуализировано

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

> This summary is a repo-only evidence surface for technical-debt
> interpretation and prioritization. It should guide investigation and
> sequencing, but it does not replace canonical architecture or governance
> documents in `docs/00-05`.
>
> Примечание о rebaseline (2026-03-24): этот pack остаётся полезным как
> historical trigger evidence для debt-wave решений от `2026-03-20/21`, но
> часть прежних current-tense hotspot recommendations уже не отражает live
> priority order после последующих bounded closeout waves. В частности,
> `crossref/batch.py` больше не является крупным mixed-responsibility hotspot:
> текущий файл — `24` LOC compatibility facade поверх split collaborators.
> Дополнительно live architecture-metric exemption baseline сейчас содержит
> `2` active file-size-limit exemptions и не содержит active class/god-object
> exemptions. Поэтому текущий active debt posture лучше читать как
> topology/ownership watchlist с bounded active file-size waiver inventory, а не как
> open-ended exemption baseline.
> Для live prioritization используйте текущий roadmap и refreshed governance
> summaries, а не только этот dated pack.

## Live File Size Exemption Inventory

Source of truth: `configs/quality/architecture_metric_exemptions.yaml` and
`configs/quality/debt_scorecard.yaml`.

| Path | Owner | Expires | Removal Step |
| ---- | ----- | ------- | ------------ |
| `src/bioetl/composition/providers/_chembl_target_protein_classification_data_source.py` | @bioetl-platform | 2026-12-31 | Split target enrichment and relation-builder/hierarchy resolution into smaller composition helpers once the protein-classification surface stabilizes. |
| `src/bioetl/interfaces/cli/commands/domains/health/observability_backend_runtime.py` | observability-dashboards | 2026-12-31 | Split module into smaller focused helpers once backend dashboard wiring is fully refactored. |

## Gate Status

| Pillar                          | Gate     | Notes                          |
| ------------------------------- | -------- | ------------------------------ |
| `dependency-hotspots`           | `PASSED` | 7 semantic EV objects created  |
| `duplication-dead-code`         | `PASSED` | 7 semantic EV objects created  |
| `ownership-compatibility-seams` | `PASSED` | 6+ semantic EV objects created |
| `complexity-hotspots`           | `PASSED` | 8 semantic EV objects created  |

## Pillar Outputs

- [dependency-hotspots/SUMMARY.md](dependency-hotspots/SUMMARY.md)
- [duplication-dead-code/SUMMARY.md](duplication-dead-code/SUMMARY.md)
- [ownership-compatibility-seams/SUMMARY.md](ownership-compatibility-seams/SUMMARY.md)
- [complexity-hotspots/SUMMARY.md](complexity-hotspots/SUMMARY.md)
- [03-synthesis/CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md)
- [04-decisions/DECISIONS.yaml](04-decisions/DECISIONS.yaml)
- [04-decisions/TECHNICAL-DEBT-ROADMAP.md](04-decisions/TECHNICAL-DEBT-ROADMAP.md)
- [05-risks/RISKS.yaml](05-risks/RISKS.yaml)
- [05-execution-plan/TECHNICAL-DEBT-EXECUTION-PLAN.md](05-execution-plan/TECHNICAL-DEBT-EXECUTION-PLAN.md)
- [ORCHESTRATION.md](ORCHESTRATION.md)
- [../residual-test-ci-debt/SUMMARY.md](../residual-test-ci-debt/SUMMARY.md)

## Strongest Technical Debt Findings

1. Dependency debt is concentrated less in policy violations and more in dense, allowed seams, especially inside `src/bioetl/interfaces/cli/commands`, storage, and selected application seams.
1. The strongest historical reducible duplication hotspot in this pack was provider-registry resolution and provider-family registration assembly scaffolding, but the live repo now treats that area as a guarded compatibility/watchlist seam rather than an active duplication wave.
1. Several apparent dead-code candidates are actually sanctioned compatibility surfaces, including `batch_execution_*` wrappers and `dependency_join_support.py`.
1. Ownership debt is now concentrated in retained convenience seams and mirrored registry access as watchlist topology rather than waiver-backed cleanup, especially around `PipelineConfigLoader`, `registration.py`, and default `ProviderRegistry` access paths.
1. Complexity debt is now more about preventing new hotspots while carrying a small bounded waiver inventory; some earlier hotspot candidates in this pack should now be read as historical trigger evidence rather than the live next split target.
1. Report/test disagreement is now mostly soft governance debt, not hard breakage: tests often enforce decoupling while some evidence interpretations age faster than the underlying code.

## Contradictions And Tensions

- `registration.py` is green under direct decoupling tests, and the live repo now treats that area as a guarded compatibility seam; older evidence language remains useful mostly as historical context for why the watchlist exists.
- Dependency-map policy is clean, but hotspot evidence still shows strong concentration in a small number of large allowed seams, now led by CLI commands and storage rather than adapters.
- Some thin wrappers look like duplication or dead code at first glance, but repo guardrails and evidence packs classify them as intentional compatibility infrastructure.
- The repo now carries a small active architecture-metric exemption baseline; older “live hotspot” narratives in this pack still need explicit rebaseline notes rather than direct execution.

## Remaining Gaps

- A dedicated follow-up pack for residual test/CI debt now exists in `docs/reports/evidence/residual-test-ci-debt/`, and the repo now has tracked governance artifacts for the ranked queue, fixture-governance ledger, CI coverage-surface matrix, environment-limited-green policy, and weak-surface-to-watchlist map; the remaining gap is implementation follow-through and stale wording cleanup, not missing planning artifacts.
- A dedicated evidence pillar for storage-specific write path complexity versus adapter-side complexity now exists in `docs/reports/evidence/storage-vs-adapter-complexity/`; the remaining question is whether future hotspot governance should reopen a bounded storage-focused wave, not whether the comparison is still missing.
- The roadmap is now prioritized, but it still remains a recommended sequence rather than an accepted decision ledger.
- The new top-level `DECISIONS.yaml` / `RISKS.yaml` pair captures the accepted posture, while detailed sequencing still lives in the roadmap and execution-plan artifacts.

## Recommended Next Steps

1. Use [CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md) as the current cross-pillar interpretation baseline.
1. Use [TECHNICAL-DEBT-ROADMAP.md](04-decisions/TECHNICAL-DEBT-ROADMAP.md) as the recommended priority order for the next refactor waves.
1. Use [TECHNICAL-DEBT-EXECUTION-PLAN.md](05-execution-plan/TECHNICAL-DEBT-EXECUTION-PLAN.md) as the current implementation sequence.
1. Treat `duplication-dead-code` evidence as a cleanup candidate ledger, not as blanket delete authorization.
1. Use [complexity-hotspots/SUMMARY.md](complexity-hotspots/SUMMARY.md) as historical trigger evidence for the completed CrossRef hotspot wave unless a fresh evidence pass reopens that seam.
1. Use [../residual-test-ci-debt/06-backlog/BACKLOG-residual-test-ci-debt-implementation-2026-04-01.md](../residual-test-ci-debt/06-backlog/BACKLOG-residual-test-ci-debt-implementation-2026-04-01.md) together with [../../../../configs/quality/test_structural_watchlist_map.yaml](../../../../configs/quality/test_structural_watchlist_map.yaml) as the current ranked queue and family-level bridge for CI/test hardening work.

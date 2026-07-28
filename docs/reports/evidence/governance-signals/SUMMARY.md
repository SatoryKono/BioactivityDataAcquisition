# Сбор evidence завершён: governance-signals

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Update note (2026-04-08): the `2026-03-24` table below remains the last reviewed duplication snapshot, but the tracked hotspot families now also carry bounded non-regression caps for `files_ge_250_loc` and `max_internal_fan_in` at the reviewed baseline. The same governance wave also turned provider contract snapshots into an explicit bounded rollout slice: `fixture_governance.contract_snapshot_registry` now tracks the managed Crossref/OpenAlex snapshot set, its update path, and the canonical drift-test modules.

Update note (2026-05-20): the hotspot-family evidence was refreshed from
`reports/quality/hotspot-duplication-baseline.json` and
`reports/quality/hotspot-family-baseline.json`. Current governance no longer
claims zero duplication for the tracked families; it enforces non-growth
budgets from the reviewed baseline and keeps zero-duplication as the next
ratchet target.

Update note (2026-05-24): the `application/core` family baseline was tightened
after the service-protocol split and `record_processor_config` extraction.
The reviewed artifact now pins `files_ge_250_loc=12` and
`max_internal_fan_in=14` for `application/core`, and the primary fan-in module
shifted from `bioetl.application.core.config` to
`bioetl.application.core.batch_runtime_failure_policy`.

**Создано объектов evidence:** 12
**Gate Статус:** PASSED

## Сводка evidence

| ID                                                                                  | Claim Summary                                                                                                                                                                                                                                                                                        | Confidence |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-governance-signals-c901-enforceable-baseline-is-green                            | The current enforceable C901 signal is green with 0 current/new violations and 7 baseline violations resolved.                                                                                                                                                                                       | 0.97       |
| EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots          | The file-size ratchet governs exemption entries, not the whole raw size-hotspot tail.                                                                                                                                                                                                                | 0.95       |
| EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero                  | The scorecard tightened file-size governance from a historical baseline of 6 to an enforceable baseline of 0.                                                                                                                                                                                        | 0.94       |
| EV-governance-signals-rf023-establishes-report-only-family-baseline                 | RF-023 keeps hotspot governance report-only at the repo level while activating bounded family-level duplication, file-growth, and fan-in non-growth ratchets from the reviewed baseline.                                                                                                             | 0.96       |
| EV-governance-signals-application-core-remains-the-primary-structural-pressure-zone | `application/core` now has 8 duplication clusters, 12 files at or above 250 LOC, and max internal fan-in 14; it remains the primary tracked family and its bounded-growth budgets were ratcheted down to the confirmed baseline.                                                                    | 0.97       |
| EV-governance-signals-bootstrap-runtime-pressure-is-contained                       | `composition/bootstrap/runtime` now has 5 duplication clusters, 5 files at or above 250 LOC, and max internal fan-in 6; its posture is controlled and remains below the bounded growth ceiling.                                                                                                    | 0.94       |
| EV-governance-signals-pipeline-factories-show-localized-duplication                 | `composition/factories/pipeline` now has 0 duplication clusters while file-growth and family-internal fan-in remain bounded at 4/4.                                                                                                                           | 0.96       |
| EV-governance-signals-makefile-now-exposes-repeatable-report-only-hotspot-command   | `python -m scripts.engineering.qa report-duplication-baseline` now generates repeatable report-only duplication artifacts for the tracked hotspot families.                                                                                                                                           | 0.95       |
| EV-governance-signals-hotspot-report-now-appends-trend-history                      | The hotspot duplication report now appends JSONL history so the next refactor waves can be compared without inventing a new gate.                                                                                                                                                                    | 0.94       |
| EV-governance-signals-top-duplicate-pairs-now-surface-backlog-slices                | The hotspot report now surfaces recurring duplicate pairs, making the backlog slices inside `application/core` and `composition/factories/pipeline` explicit.                                                                                                                                        | 0.94       |
| EV-governance-signals-rf023-first-downward-move-landed                              | The latest reviewed `2026-05-24` snapshot keeps five tracked families and records 39 total duplication clusters; governance now uses these as explicit baseline budgets rather than stale zero claims, and `application/core` was ratcheted to the improved file-growth/fan-in baseline.          | 0.98       |
| EV-governance-signals-duplication-governance-still-avoids-premature-global-ratchet  | Hotspot governance still avoids a premature global ratchet: bounded family-level duplication, file-growth, and fan-in enforcement is active for tracked families, while repo-level hotspot governance remains report-only.                                                                            | 0.97       |

## RF-023 hotspot family baseline and updated trend check (2026-05-24)

| Family                           | Duplication clusters | Files >=250 LOC | Helper function ratio | Max fan-in | Owner                  | Expected action                                                                           | Trend                                                                                                                                             |
| -------------------------------- | -------------------: | --------------: | --------------------: | ---------: | ---------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `application/core`               |                    8 |              12 |                 0.375 |         14 | `@bioetl-architecture` | Active non-growth ratchet; cap duplication, file-growth, and fan-in at the reviewed baseline. | Service protocol decomposition plus `record_processor_config` extraction allowed a downward ratchet to `files_ge_250_loc=12` and `max_internal_fan_in=14`. |
| `composition/bootstrap/runtime`  |                    5 |               5 |                 0.351 |          6 | `@bioetl-platform`     | Active non-growth ratchet; cap duplication, file-growth, and fan-in at the reviewed baseline. | Composite runtime cleanup keeps the family below its bounded growth ceiling while duplicate clusters remain visible. |
| `composition/factories/pipeline` |                    0 |               4 |                 0.470 |          4 | `@bioetl-platform`     | Active non-growth ratchet; cap duplication, file-growth, and fan-in at the reviewed baseline. | Duplication is now clean, but file-growth and fan-in stay pinned at the reviewed ceiling. |
| `application/services/control_plane` |                15 |              22 |                 0.496 |          6 | `@bioetl-platform`     | Reviewed baseline; cap duplication, file-growth, and fan-in while diagnostics debt is paid down. | Diagnostics helper extraction reduced the family to 15 duplicate clusters while size and fan-in remain bounded. |
| `composition/runtime_builders`   |                   13 |               7 |                 0.502 |         11 | `@bioetl-platform`     | Reviewed baseline; cap duplication, file-growth, and fan-in while runtime-builder seams are consolidated. | Runtime-builder duplication remains visible and is bounded at the refreshed baseline. |

## Ключевые выводы

- `C901` remains green, so structural-pressure discussions can focus on hotspot families rather than baseline complexity noise.
- The refreshed RF-023 layer shows five tracked families with explicit non-growth budgets rather than stale zero-duplication claims. `application/core` still remains the primary watch zone, but its confirmed improvement allowed a downward ratchet from `14/15` to `12/14`.
- The tracked families now share the same governance posture: duplication is report-only at the repo level but bounded per family, while `files_ge_250_loc` and `max_internal_fan_in` remain hard non-growth checks.
- Governance is now more actionable because each tracked family has an owner, an expected action, and a stated ratchet posture instead of a raw number without follow-up.
- Replay/fixture governance is also more explicit now: provider contract snapshots are no longer only implied by `partial` rollout state, but anchored to a matrix-declared bounded registry covering the current Crossref/OpenAlex slice together with its drift tests and update path.
- Trend capture is now operationalized through an append-only hotspot history artifact, and the latest reviewed comparison point totals `39` duplication clusters across five tracked families.
- The latest reviewed hotspot report still has current `R0801` findings in every tracked family, so the active ratchet is a non-growth control rather than a clean-state claim.

## Отмеченные противоречия

- There is still no contradiction between a green exemption ratchet and a broad raw hotspot tail; these controls answer different governance questions.
- There is no contradiction between keeping duplication report-only and adding baseline metrics; the metrics are intended to prioritize backlog slices, not to block unrelated delivery.

## Оставшиеся пробелы

- A bounded family-level non-growth ratchet is now active for the tracked families because the refreshed hotspot baselines are explicit. The remaining gap is to pay down the current `R0801` clusters and only then promote individual families to zero-duplication ratchets.
- Provider contract snapshots are still only a bounded partial rollout. The current registry is intentionally limited to Crossref/OpenAlex, so the remaining gap is representative breadth rather than missing local drift diagnostics or an undefined update path.
- Helper density is a lightweight heuristic based on underscore-prefixed functions; it is useful for prioritization, but not a standalone design-quality verdict.
- Fan-in is currently a local import-based indicator, not a full SCC/dependency-cycle analysis.

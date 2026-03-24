# Сбор evidence завершён: governance-signals

**Создано объектов evidence:** 12  
**Gate Статус:** PASSED

## Сводка evidence

| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-governance-signals-c901-enforceable-baseline-is-green | The current enforceable C901 signal is green with 0 current/new violations and 7 baseline violations resolved. | 0.97 |
| EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots | The file-size ratchet governs exemption entries, not the whole raw size-hotspot tail. | 0.95 |
| EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero | The scorecard tightened file-size governance from a historical baseline of 6 to an enforceable baseline of 0. | 0.94 |
| EV-governance-signals-rf023-establishes-report-only-family-baseline | RF-023 keeps hotspot governance report-only at the repo level while activating bounded family-level duplication ratchets for zero-duplication families after a second confirming clean snapshot. | 0.96 |
| EV-governance-signals-application-core-remains-the-primary-structural-pressure-zone | `application/core` now has 0 duplication clusters, but it still carries the largest large-file tail and max internal fan-in of the tracked families. | 0.96 |
| EV-governance-signals-bootstrap-runtime-pressure-is-contained | `composition/bootstrap/runtime` now has 0 duplication clusters, while still carrying 3 files at or above 250 LOC and max internal fan-in of 5, so its remaining posture is watchful rather than cleanup-heavy. | 0.93 |
| EV-governance-signals-pipeline-factories-show-localized-duplication | `composition/factories/pipeline` now has 0 duplication clusters, while still carrying 3 files at or above 250 LOC and max internal fan-in of 6, so its remaining posture is watchful rather than cleanup-heavy. | 0.95 |
| EV-governance-signals-makefile-now-exposes-repeatable-report-only-hotspot-command | `make qa-hotspot-report` now generates repeatable report-only duplication artifacts for the tracked hotspot families. | 0.95 |
| EV-governance-signals-hotspot-report-now-appends-trend-history | The hotspot duplication report now appends JSONL history so the next refactor waves can be compared without inventing a new gate. | 0.94 |
| EV-governance-signals-top-duplicate-pairs-now-surface-backlog-slices | The hotspot report now surfaces recurring duplicate pairs, making the backlog slices inside `application/core` and `composition/factories/pipeline` explicit. | 0.94 |
| EV-governance-signals-rf023-first-downward-move-landed | The latest reviewed `2026-03-24` snapshot is down versus `2026-03-23`: total duplication clusters moved from `26` to `0`, driven by `application/core` moving from `21` to `0`, `composition/bootstrap/runtime` moving from `1` to `0`, and `composition/factories/pipeline` moving from `4` to `0`. | 0.98 |
| EV-governance-signals-duplication-governance-still-avoids-premature-global-ratchet | Duplication governance still avoids a premature global ratchet: family-level duplication-only enforcement is now active for the three zero-duplication families, while repo-level governance and non-duplication metrics remain report-only/watch-only. | 0.97 |

## RF-023 hotspot family baseline and updated trend check (2026-03-24)

| Family | Duplication clusters | Files >=250 LOC | Helper function ratio | Max fan-in | Owner | Expected action | Trend |
|--------|----------------------:|----------------:|----------------------:|-----------:|-------|-----------------|-------|
| `application/core` | 0 | 18 | 0.460 | 22 | `@bioetl-architecture` | Active duplication-only ratchet; keep file-growth/fan-in watch-only. | Down `-21` on `2026-03-24` vs `2026-03-23`; the second clean `2026-03-24` snapshot now keeps the bounded duplication non-regression check active. |
| `composition/bootstrap/runtime` | 0 | 3 | 0.333 | 5 | `@bioetl-platform` | Active duplication-only ratchet; keep file-growth/fan-in watch-only. | Down `-1` on `2026-03-24` vs `2026-03-23`; the second clean `2026-03-24` snapshot now keeps the bounded duplication non-regression check active. |
| `composition/factories/pipeline` | 0 | 3 | 0.469 | 6 | `@bioetl-platform` | Active duplication-only ratchet; keep file-growth/fan-in watch-only. | Down `-4` on `2026-03-24` vs `2026-03-23`; the second clean `2026-03-24` snapshot now keeps the bounded duplication non-regression check active. |

## Ключевые выводы

- `C901` remains green, so structural-pressure discussions can focus on hotspot families rather than baseline complexity noise.
- The new RF-023 layer now shows all three tracked families at zero duplication. `application/core` still carries the largest large-file tail and the highest local fan-in of the tracked families, so it remains the primary watch zone even after duplication cleanup reached zero.
- The three tracked families now share the same duplication posture: zero current residue and an active family-level duplication ratchet, while overall governance still stays report-only at the repo level. That keeps CI bounded to non-regression on duplication without turning file-growth or fan-in into premature blockers.
- Governance is now more actionable because each tracked family has an owner, an expected action, and a stated ratchet posture instead of a raw number without follow-up.
- Trend capture is now operationalized through an append-only hotspot history artifact, and the latest reviewed comparison point now totals `0` duplication clusters across the tracked families.
- The latest reviewed hotspot report has no current `R0801` findings in the tracked families; the remaining governance pressure is now carried by file-growth and fan-in rather than duplication, which is why the active ratchet remains duplication-only.

## Отмеченные противоречия

- There is still no contradiction between a green exemption ratchet and a broad raw hotspot tail; these controls answer different governance questions.
- There is no contradiction between keeping duplication report-only and adding baseline metrics; the metrics are intended to prioritize backlog slices, not to block unrelated delivery.

## Оставшиеся пробелы

- A bounded duplication-only ratchet is now active for the tracked families because the history artifact contains a second confirming clean snapshot; file-growth and fan-in still remain watch-only until a later governance wave proves those signals are actionable enough for enforcement.
- Helper density is a lightweight heuristic based on underscore-prefixed functions; it is useful for prioritization, but not a standalone design-quality verdict.
- Fan-in is currently a local import-based indicator, not a full SCC/dependency-cycle analysis.

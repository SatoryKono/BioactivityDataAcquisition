# Сбор evidence завершён: governance-signals

**Создано объектов evidence:** 9  
**Gate Статус:** PASSED

## Сводка evidence

| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-governance-signals-c901-enforceable-baseline-is-green | The current enforceable C901 signal is green with 0 current/new violations and 7 baseline violations resolved. | 0.97 |
| EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots | The file-size ratchet governs exemption entries, not the whole raw size-hotspot tail. | 0.95 |
| EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero | The scorecard tightened file-size governance from a historical baseline of 6 to an enforceable baseline of 0. | 0.94 |
| EV-governance-signals-rf023-establishes-report-only-family-baseline | RF-023 adds a report-only family baseline for `application/core`, `composition/bootstrap/runtime`, and `composition/factories/pipeline` instead of introducing a repo-wide hard gate. | 0.96 |
| EV-governance-signals-application-core-is-the-primary-structural-pressure-zone | `application/core` is the dominant tracked hotspot family with 21 duplication clusters, 18 files at or above 250 LOC, and max internal fan-in of 22. | 0.93 |
| EV-governance-signals-bootstrap-runtime-pressure-is-contained | `composition/bootstrap/runtime` has measurable but contained pressure with 1 duplication cluster, 3 files at or above 250 LOC, and max internal fan-in of 5. | 0.91 |
| EV-governance-signals-pipeline-factories-show-localized-duplication | `composition/factories/pipeline` shows localized duplication pressure with 4 duplication clusters, 3 files at or above 250 LOC, and max internal fan-in of 6. | 0.92 |
| EV-governance-signals-makefile-now-exposes-repeatable-report-only-hotspot-command | `make qa-hotspot-report` now generates repeatable report-only duplication artifacts for the tracked hotspot families. | 0.95 |
| EV-governance-signals-hotspot-report-now-appends-trend-history | The hotspot duplication report now appends JSONL history so the next refactor waves can be compared without inventing a new gate. | 0.94 |
| EV-governance-signals-duplication-governance-still-avoids-premature-global-ratchet | Duplication governance still avoids a premature global ratchet and defers any family-level enforcement until after one or two successful refactor waves. | 0.97 |

## RF-023 hotspot family baseline (2026-03-23)

| Family | Duplication clusters | Files >=250 LOC | Helper function ratio | Max fan-in | Owner | Expected action | Trend |
|--------|----------------------:|----------------:|----------------------:|-----------:|-------|-----------------|-------|
| `application/core` | 21 | 18 | 0.460 | 22 | `@bioetl-architecture` | Split helper-heavy orchestration seams and reduce fan-in before any family ratchet. | Baseline opened; must trend down across the next refactor waves. |
| `composition/bootstrap/runtime` | 1 | 3 | 0.329 | 5 | `@bioetl-platform` | Keep report-only and watch for renewed duplication during runtime/bootstrap changes. | Watch-only; stable enough to defer ratchet. |
| `composition/factories/pipeline` | 4 | 3 | 0.469 | 6 | `@bioetl-platform` | Prefer micro-slice factory seam cleanup over broad composition rewrites. | Watch-only; ratchet candidate after one successful cleanup wave. |

## Ключевые выводы

- `C901` remains green, so structural-pressure discussions can focus on hotspot families rather than baseline complexity noise.
- The new RF-023 layer makes `application/core` the clearest backlog hotspot: it combines the highest duplication pressure, the largest large-file tail, and the highest local fan-in of the tracked families.
- The two `composition` families are now measurable and comparable, but their current signals support report-only monitoring rather than immediate CI enforcement.
- Governance is now more actionable because each tracked family has an owner, an expected action, and a stated ratchet posture instead of a raw number without follow-up.
- Trend capture is now operationalized through an append-only hotspot history artifact, so the next cleanup wave can be compared against an actual prior observation rather than a prose-only baseline.

## Отмеченные противоречия

- There is still no contradiction between a green exemption ratchet and a broad raw hotspot tail; these controls answer different governance questions.
- There is no contradiction between keeping duplication report-only and adding baseline metrics; the metrics are intended to prioritize backlog slices, not to block unrelated delivery.

## Оставшиеся пробелы

- This summary now has a family-level baseline and a history capture path, but not yet a second observation point; trend is still "baseline opened" or "watch", not a numerical delta.
- Helper density is a lightweight heuristic based on underscore-prefixed functions; it is useful for prioritization, but not a standalone design-quality verdict.
- Fan-in is currently a local import-based indicator, not a full SCC/dependency-cycle analysis.

# Сбор evidence завершён: governance-signals

**Создано объектов evidence:** 7  
**Gate Статус:** PASSED

## Сводка evidence

| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-governance-signals-c901-enforceable-baseline-is-green | The current enforceable C901 signal is green with 0 current/new violations and 7 baseline violations resolved. | 0.97 |
| EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots | The file-size ratchet governs exemption entries, not the whole raw size-hotspot tail. | 0.95 |
| EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero | The scorecard tightened file-size governance from a historical baseline of 6 to an enforceable baseline of 0. | 0.94 |
| EV-governance-signals-hotspot-budgets-prioritize-application-core | Named hotspot budgeting currently prioritizes `src/bioetl/application/core/`, not the full raw hotspot inventory. | 0.90 |
| EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences | An ad hoc duplication scan reports 31 `R0801` occurrences in `composition`. | 0.88 |
| EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences | An ad hoc duplication scan reports 88 `R0801` occurrences in `application`. | 0.89 |
| EV-governance-signals-duplication-governance-excludes-composition-and-application | Default duplication governance does not ratchet `composition` or `application`; it only scans `infrastructure/adapters`. | 0.96 |

## Ключевые выводы

- `C901` is currently in a clean enforceable state, so complexity debt is not adding baseline noise to the next refactor wave.
- The size ratchet is stricter than the raw tree inventory: the enforceable file-size exemption budget is zero, but the codebase still has a broad size tail (`82` files `>10 KB`, `10` files `>350 LOC`).
- Named hotspot budgets are targeted, not universal; the scorecard explicitly prioritizes `application/core` rather than encoding the whole repo-wide size tail as a ratcheted hotspot program.
- `composition` and especially `application` show meaningful duplication pressure in live scans, but that pressure is not currently tracked by an enforceable historical budget.

## Отмеченные противоречия

- There is no direct contradiction between a green file-size exemption ratchet and a large raw hotspot tail; they are different controls.
- There is no contradiction between the ad hoc duplication counts and the Makefile governance target; the mismatch is one of measurement scope, not conflicting data.

## Оставшиеся пробелы

- This pack does not yet include a time series for duplication in `composition` or `application`, only a current snapshot.
- The duplication counts are from pylint `R0801` and have not been normalized for intentional facades, export barrels, or compatibility shims.
- The size-hotspot evidence stops at file-level inventory and does not yet link the large-file tail to churn, ownership, or defect history.


## Pre-PR Verification Notes
- The required checks `report-architecture-debt-remote-main-baseline` and `report-debt-governance-gates` currently fail on `main`.
- **Blocker**: `test_governance_budget_violations` (current=1, refined_assertless_tests budget=0). This was triggered by `tests/unit/infrastructure/schemas/test_rf002_extra_forbid_migration.py::test_rf002_strict_leaves_reject_unknown_keys`.
- Per user directive, we are **not** modifying foreign test files or increasing the debt budget. This blocker is reported back to the repository owner and prevents final full integration pass locally, but does not invalidate the variant C checkout/history optimizations findings (which are already verified in `main`).

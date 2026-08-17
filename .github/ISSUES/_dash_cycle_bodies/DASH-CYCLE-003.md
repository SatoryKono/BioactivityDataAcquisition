Parent: #8944  
Plan: `reports/observability/remediation/20260817/plan_dashboard_cycle1.md` WP-2  
Leftover from: #8937 (GRAF-TRUST-06 claimed inventory closeout; YAML was updated, the generator was not)

## Problem

The static panel-matrix contract fails because the generator baseline is still 226 while the shipped seven-UID inventory is 235.

Current tree (`origin/main` and `fix/graf-trust-8935-8941`):

| Surface | Count |
| --- | ---: |
| `grafana/dashboards/*.json` leaf+row | 235 (206 non-row + 29 row) |
| `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml` sum | 235 (64+27+42+35+36+13+18) |
| `EXPECTED_PANEL_COUNT` in `scripts/engineering/qa/report_dashboard_panel_audit_matrix.py` | **226** |

Cycle-1 reported 234 vs 226. The extra Trust panel after GRAF-TRUST D0 is expected. `report-dashboard-inventory --check` already agrees with YAML. The failing gate is the **second** baseline in the panel-audit-matrix generator and `tests/integration/test_dashboard_panel_audit_matrix_contract.py`.

This is lockstep with the live inventory, **not** a quality-budget increase. Do not hide growth and do not relax `--check`.

## Work

- Derive the expected count from `dashboard-inventory.yaml` (sum of `panel_count` for the seven shipped UIDs) **or** compare `len(_collect_rows())` to that sum.
- Stop hardcoding 226. Comment must cite the YAML contract, not #8269 / 223.
- Keep the fail-closed drift test. Assert the seven UIDs and unique `(uid, panel_id)`.
- Do not change YAML counts unless JSON actually changed.

## Acceptance

- [ ] `python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check` exits 0 against 235 live rows
- [ ] `python -m scripts.engineering.qa report-dashboard-inventory --check --json` still green
- [ ] `tests/integration/test_dashboard_panel_audit_matrix_contract.py` passes
- [ ] A one-row inventory drift still fails closed
- [ ] No debt-budget / exemption / threshold change

## Constraints

- Generator + contract test only. No dashboard JSON rewrite here (that is #8946 / DASH-CYCLE-001)
- Do not reopen #8937
- No `.env` mutation

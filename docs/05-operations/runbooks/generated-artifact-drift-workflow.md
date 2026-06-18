# Generated Artifact Drift Workflow

This runbook is the local/CI workflow for generated artifact drift. It is a
workflow mirror only; it does not redefine runtime behavior. Canonical runtime
behavior remains in `.codex/**`, `.gemini/**`, ADRs, and source code.

## Scope

Use this workflow when touching generated evidence, config governance, VCR
metadata, date-only compatibility inventories, or debt closeout reports.

## Required Commands

Run the same commands locally and in CI:

| Surface | Check command | Refresh command |
| --- | --- | --- |
| Config comparison matrix | `python -m scripts.schema generate-config-matrix --check` | `python -m scripts.schema generate-config-matrix --update` |
| Config duplication/backlog audit | `pytest tests/architecture/test_config_surface_entity_residual_plateau.py` | `python -m scripts.engineering.qa.report_config_surface_backlog` |
| Config discrepancy drift | `pytest tests/architecture/test_config_discrepancy_report_drift.py tests/architecture/test_config_discrepancy_metrics_ratchets.py` | `python -m scripts.schema generate-config-matrix --update` |
| VCR metadata catalog | `python -m scripts.engineering.qa report-vcr-metadata --check` | `python -m scripts.engineering.qa report-vcr-metadata --update` |
| Date-only content-hash inventory | `pytest tests/architecture/test_content_hash_datetime_policy_inventory.py` | Edit `configs/quality/determinism_identity_policy.yaml`; do not add budget. |
| Debt closeout inventory | `pytest tests/architecture/test_tech_debt_issues_5343_5346_closeout.py tests/architecture/test_tech_debt_issues_5387_5394_closeout.py` | Add issue-specific closeout evidence and guard tests. |
| Hotspot family baseline | `python -m scripts.engineering.qa report-family-baseline --check` | `python -m scripts.engineering.qa report-family-baseline --update` |
| Contract coverage matrix | `python -m scripts.engineering.qa report-contract-coverage-matrix --check` | `python -m scripts.engineering.qa report-contract-coverage-matrix --update` |

## Debt Outcome

Every generated-artifact drift closeout must report one of:

| Outcome | Meaning | Allowed action |
| --- | --- | --- |
| `decreased` | A tracked debt count, warning count, or residual inventory decreased. | Commit evidence and ratchet if applicable. |
| `flat` | Counts stayed unchanged and no budget increased. | Commit evidence if it closes visibility or drift. |
| `increased` | Any tracked debt count, warning count, stale artifact count, or residual inventory increased. | Stop for architecture review. Do not increase budgets. |

Budget edits are not a remedy for drift. If an increase is real, record the
review and remediation plan; do not relax `configs/quality/debt_scorecard.yaml`
or other ratchets as part of the closeout.

## Closeout Evidence

Closeout evidence must include:

- The changed generated artifacts under `reports/quality/**` or the exact reason
  the artifact is unchanged.
- The matching architecture guard or generator `--check` command.
- A `decreased`, `flat`, or `increased` debt outcome.
- A statement that no technical-debt budget was increased.

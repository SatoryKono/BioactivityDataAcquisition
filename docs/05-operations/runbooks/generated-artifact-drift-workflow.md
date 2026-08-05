______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-08-05'

______________________________________________________________________

# Generated Artifact Drift Workflow

## Trigger

- Use this runbook when generated repo artifacts drift from their generators or
  architecture guard baselines.
- Use it for local or CI failures involving generated evidence, config
  governance inventories, VCR metadata, date-only compatibility inventories, or
  debt closeout reports.

## Impact

- Priority: P2.
- Leaving generated artifacts stale hides governance drift and makes CI results
  non-reproducible across local and automation environments.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem
  storage, MemoryLock.
- Required access: repository checkout, local shell, the impacted generator or
  guard test, and the affected artifact path under `reports/**`, `configs/**`,
  or `docs/**`.
- Confirm whether the failure is a true generator mismatch or an intentional
  behavior change that still lacks regenerated evidence.

## Procedure

### 1. Identify the drift family

Use the failing test or CI step to place the mismatch into one of the governed
artifact families below.

### 2. Run the matching check and refresh commands

Run the same commands locally and in CI:

| Surface | Check command | Refresh command |
| --- | --- | --- |
| Config comparison matrix | `python -m scripts.schema generate-config-matrix --check` | `python -m scripts.schema generate-config-matrix --update` |
| Config duplication/backlog audit | `pytest tests/architecture/test_config_surface_entity_residual_plateau.py` | `python -m scripts.engineering.qa.report_config_surface_backlog` |
| Config discrepancy drift | `pytest tests/architecture/test_config_discrepancy_report_drift.py tests/architecture/test_config_discrepancy_metrics_ratchets.py` | `python -m scripts.schema generate-config-matrix --update` |
| Module coverage inventory | `python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml` | `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml` |
| Test governance snapshots | `python -m scripts.engineering.qa.report_test_governance_audit --check` | `python -m scripts.engineering.qa.report_test_governance_audit --json-out reports/quality/test-governance-current.json --fixture-duplication-out reports/quality/test-fixture-asset-duplication.json` |
| Documentation cleanup inventory | `python -m scripts.docs.checks.documentation_cleanup_inventory --check` | `python -m scripts.docs.checks.documentation_cleanup_inventory --update` |
| Architecture dependency map | `python -m scripts.engineering.qa.generate_architecture_dependency_map --check` | `python -m scripts.engineering.qa.generate_architecture_dependency_map --update` |
| Committed test telemetry | `pytest tests/architecture/test_test_telemetry_baseline.py tests/architecture/test_test_telemetry_governance.py` | `python -m scripts.engineering.ci.update_test_telemetry_baseline --coverage-percent <percent> --source-branch main --source-commit <reachable-commit> --source-run-id <run-id>` |
| Compatibility importer census | `python -m scripts.engineering.qa report-compatibility-importer-census --check` | `python -m scripts.engineering.qa report-compatibility-importer-census --update` |
| Architecture artifact duplication | `python -m scripts.engineering.qa.report_artifact_duplication_audit --check` | `python -m scripts.engineering.qa.report_artifact_duplication_audit --json-out reports/quality/config-contract-registry-artifact-duplication.json` |
| Flaky-test burndown review | `python -m scripts.engineering.qa.report_flaky_test_burndown_review --check` | `python -m scripts.engineering.qa.report_flaky_test_burndown_review` |
| Live residual snapshot | `python -m scripts.engineering.qa.report_live_residual_snapshot --check` | `python -m scripts.engineering.qa.report_live_residual_snapshot` |
| Debt-governance rollup | `python -m scripts.engineering.qa.report_debt_governance_gates --check` | `python -m scripts.engineering.qa.report_debt_governance_gates --update` |
| VCR metadata catalog | `python -m scripts.engineering.qa report-vcr-metadata --check` | `python -m scripts.engineering.qa report-vcr-metadata --update` |
| Date-only content-hash inventory | `pytest tests/architecture/test_content_hash_datetime_policy_inventory.py` | Edit `configs/quality/determinism_identity_policy.yaml`; do not add budget. |
| Debt closeout inventory | `pytest tests/architecture/test_tech_debt_issues_5343_5346_closeout.py tests/architecture/test_tech_debt_issues_5387_5394_closeout.py` | Add issue-specific closeout evidence and guard tests. |
| Hotspot family baseline | `python -m scripts.engineering.qa report-family-baseline --check` | `python -m scripts.engineering.qa report-family-baseline --update` |
| Contract coverage matrix | `python -m scripts.engineering.qa report-contract-coverage-matrix --check` | `python -m scripts.engineering.qa report-contract-coverage-matrix --update` |

### 3. Classify the debt outcome

Every generated-artifact drift closeout must report one of:

| Outcome | Meaning | Allowed action |
| --- | --- | --- |
| `decreased` | A tracked debt count, warning count, or residual inventory decreased. | Commit evidence and ratchet if applicable. |
| `flat` | Counts stayed unchanged and no budget increased. | Commit evidence if it closes visibility or drift. |
| `increased` | Any tracked debt count, warning count, stale artifact count, or residual inventory increased. | Stop for architecture review. Do not increase budgets. |

Budget edits are not a remedy for drift. If an increase is real, record the
review and remediation plan; do not relax `configs/quality/debt_scorecard.yaml`
or other ratchets as part of the closeout.

### 4. Capture closeout evidence

Closeout evidence must include:

- The changed generated artifacts under `reports/quality/**` or the exact reason
  the artifact is unchanged.
- The matching architecture guard or generator `--check` command.
- A `decreased`, `flat`, or `increased` debt outcome.
- A statement that no technical-debt budget was increased.

### 5. Re-run the guard

After regenerating the artifact, re-run the corresponding `--check` command or
architecture test before closing the task.

## Compliance

- This runbook governs the generated-artifact drift surface on `main`; it is no
  longer an ungoverned mirror note.
- Generated-artifact drift closeout MUST preserve the repository guardrail that
  technical-debt budgets cannot increase.

## Verification

- Confirm the regenerated artifact matches the current code/config/docs source.
- Confirm the paired `--check` command or architecture test now passes.
- Confirm the closeout note states `decreased`, `flat`, or `increased` and
  explicitly says no debt budget was increased.

## Rollback

- If regeneration reveals an unintended behavior change, revert the underlying
  code/config/doc change instead of hand-editing the artifact to match stale
  expectations.
- If the failure belongs to a different generator family than originally
  assumed, stop and reroute to the correct generator or architecture owner.

## Post-incident

- Record the artifact family, failing guard, regeneration command, and outcome
  classification in the task or PR closeout.
- Add follow-up governance work when drift exposed a missing validator or an
  ambiguous ownership boundary.

# N1 Shadow Window Status

## 1. Nightly Window Classification (Inventory)

The `.github/workflows/nightly.yml` triggers the following workflows and checks:

### Deterministic Checks (Fixed Inputs, No External State)
- **Tests** (`tests.yml` with `generated-artifacts: true`)
- **Duplication and Complexity Checks** (`duplication-complexity.yml`)
- **Lint and Architecture Gates** (`import-linter.yml`)
- **Mutation Testing** (`mutation-testing.yml`)
- **Generated artifact assertions (daily)** (Direct job in `nightly.yml` using `scripts.engineering.ci.generated_artifact_checks`)

### Non-Deterministic / State-Dependent Checks (External/Security)
- **E2E Matrix Health** (`e2e-matrix-health.yml`)
- **Security Scans** (`security.yml`)
- **zizmor** (`zizmor.yml`)
- **CodeQL** (`codeql.yml`)
- **OpenSSF Scorecard** (`scorecard.yml`)
- **Branch Hygiene** (`branch-hygiene.yml`)
- **Quarterly GitHub Settings Review** (`github-settings-quarterly-review.yml`)

*(Note: Exact owners and specific sources of comparison are largely implicit or derived dynamically, as explicit headers/metadata were not found in the workflow definitions).*

## 2. N1 Blocker Status

- **Observation UTC:** `2026-11-05T17:35:00Z` (triage re-check of GitHub Actions + ledger).
- **Ledger window start (source of truth):** `window_start_utc=2026-11-02T07:10:42Z`, `window_start_sha=acc8d0f344a048f8d659671f59da2de279a20616` in `reports/governance/n1-shadow-window/ledger.json` (`next_window.status=started`). Wall-clock since that stamp exceeds 48 hours, but N1 is **not** closable: Nightly remains RED, comparable acceptance evidence is incomplete, and manual closure is forbidden.
- **Nightly RED evidence (verified):** run [`41959660461`](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/41959660461) (`conclusion=failure`, `created_at=2026-11-05T03:08:05Z`, `head_sha=0576b5b74c209e3a8bff8eea32980b5bbefb50f9`, attempt 1). Prior scheduled Nightly on `2026-11-04T03:07:48Z` (`41765155348`) is also `failure` on the same SHA.
- Expected Action: Wait for Nightly pipeline to be repaired before marking window as complete. (No manual closure allowed; do not edit `ledger.json` in this PR.)

## 3. Collector Evidence Mechanism

Nightly telemetry/evidence is collected securely using `scripts/engineering/ci/nightly_shadow_archive.py`.
- **API Call / Extraction:** Data is fetched via GitHub REST API (e.g. `JsonGitHubClient`).
- **Data Properties:**
  - Raw JSON format.
  - Includes `run_id`, `attempt`, and UTC timestamps.
  - Manifest generation involves creating SHA-256 checksums (`hashlib.sha256`).
  - Versioned schemas (`schema_version = 1`).
- **Outcome States:** Outcomes are explicitly partitioned (`partition_producer`).
  - Returns `success` only if the collected outcome is strictly successful.
  - Unavailable data is marked as `missing` or `unknown`.
- **Action Constraints (retention scope):** The 90-day diagnostics retention applies **only** to the upload path for the `generated-artifact-daily` job, and only when `partition_producer` classifies the outcomes of that job's two steps (`daily` and `validators`) as non-success. Whole-Nightly workflow failure is **not** an input to `partition_producer`. Therefore, if Nightly fails elsewhere but both `daily` and `validators` succeed, the success artifact is retained for **7** days (`retention-days: 7`), not 90. Cancellation uses a separate best-effort upload (`if-no-files-found: warn`), so a cancelled attempt may leave no artifact at all.

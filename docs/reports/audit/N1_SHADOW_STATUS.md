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

- Genuine 48-hour window has not elapsed yet.
- Nightly is currently RED at the start of the window.
- Expected Action: Wait for Nightly pipeline to be repaired before marking window as complete. (No manual closure allowed).

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
- **Action Constraints:** If the outcome is not explicitly `success`, evidence is placed in a diagnostics bucket with a longer retention period (90 days).

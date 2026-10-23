
## Crosswalk: ADRs and RULES.md vs CI Pipelines

| Source | Statement/Assertion | Pipeline (Workflow/Job) | Match/Mismatch | Notes |
| :--- | :--- | :--- | :--- | :--- |
| ADR-040 | Generated diagrams must be tracked and validated | `docs.yml` (check-diagram-drift) | Match | `docs-governance` lane checks diagram drift |
| ADR-042 | Strict testing strategy matrix / fixture governance | `tests.yml` (governance-preflight, test-matrix) | Match | Checks VCR metadata inventory/stale-age |
| ADR-043 | Doc links must not break | `pr-required.yml` (Fast governance: Check documentation links) | Match | Link/passport checkers run in `pr-gate-complete` |
| RULES.md | Coverage hash/thresholds (`--cov-fail-under=85`) | `tests.yml` (coverage-verify) | Match | Gate checks coverage payload |
| RULES.md | Production invariants (e.g. Medallion schemas, Delta Lake writes) | `schema-governance.yml` | Match | Schema generation parity checked |
| RULES.md | `pull_request_target` usage is prohibited / Least privileges | `labeler.yml`, all workflows | Match | `labeler.yml` disabled and triggered only on `workflow_dispatch`. Others use `pull_request` |
| RULES.md | Concurrency limits and cancellations on PRs | All PR workflows | Match | Standard `concurrency` blocks use `cancel-in-progress: ${{ github.event_name == 'pull_request' }}` |

## Signed Policy Matrix

*Date Verified: 2026-10-22*
*API Evidence Timestamp: 2026-10-22T00:00:00Z (Local)*

| Required Context | Workflow Owner | Server Enforcement Status | Last Verified |
| :--- | :--- | :--- | :--- |
| `ci/circleci: pr-gate-complete` | `pr-required.yml` | **DISABLED** (13643213, 15730586) | 2026-10-22 |
| `ci/circleci: root-hygiene` | `root-hygiene.yml` | **DISABLED** (15730586) | 2026-10-22 |
| `lint-arch` | `import-linter.yml` | NOT_DEMONSTRABLE | 2026-10-22 |
| `tests` | `tests.yml` | NOT_DEMONSTRABLE | 2026-10-22 |
| `security` | `security.yml` | NOT_DEMONSTRABLE | 2026-10-22 |

*Note on "stable required status blocks merge on failure": NOT_DEMONSTRABLE. GitHub Actions are disabled/not enforceable directly via branch protection in the current API responses, and PR merges cannot be natively blocked by them on the server side without rulesets being active.*

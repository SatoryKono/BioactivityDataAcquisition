______________________________________________________________________

Version: 1.0.0
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-10-22'

______________________________________________________________________

# CI policy matrix crosswalk

Repo-only evidence for issue #12370. This file does not change GitHub
rulesets. Catalog `enforcement_verified_date` stays `2026-10-09`: that stamp
is not proof of active merge protection. The 2026-10-22 read below is a
separate ruleset GET.

## Crosswalk: ADRs and RULES.md vs CI pipelines

| Source | Statement | Pipeline | Match | Notes |
| --- | --- | --- | --- | --- |
| ADR-040 | Generated diagrams must be tracked and validated | `docs.yml` (`check-diagram-drift`) | Match | `docs-governance` checks diagram drift |
| ADR-042 | Strict testing strategy matrix / fixture governance | `tests.yml` (`governance-preflight`, `test-matrix`) | Match | VCR metadata inventory and stale-age checks |
| ADR-043 | Doc links must not break | `pr-required.yml` (fast governance documentation links) | Match | Link and passport checkers run in `pr-gate-complete` |
| RULES.md | Coverage threshold `--fail-under=85` | `tests.yml` (`coverage-verify`) | Match | Gate checks the coverage payload |
| RULES.md | Production invariants (Medallion schemas, Delta writes) | `schema-governance.yml` | Match | Schema generation parity |
| RULES.md | Least privilege; no active `pull_request_target` | `labeler.yml` and other workflows | Match | `labeler.yml` is `workflow_dispatch` only and kept disabled |
| RULES.md | PR concurrency cancels superseded runs | PR workflows | Match | `cancel-in-progress` is tied to `pull_request` |

## Signed policy matrix

Read-only GET date: 2026-10-22. Rulesets that include `refs/heads/main`
(`13643213`, `15730586`) were `enforcement: disabled` and still stored
`ci/circleci` contexts. A stored context on a disabled ruleset is not active
CircleCI protection and is not configured GitHub Actions enforcement.

| Required context | Workflow owner | Server enforcement | Last verified |
| --- | --- | --- | --- |
| `ci/circleci: pr-gate-complete` | `pr-required.yml` | DISABLED (`13643213`, `15730586`) | 2026-10-22 |
| `ci/circleci: root-hygiene` | `root-hygiene.yml` | DISABLED (`15730586`) | 2026-10-22 |
| `lint-arch` | `import-linter.yml` | NOT_DEMONSTRABLE | 2026-10-22 |
| `tests` | `tests.yml` | NOT_DEMONSTRABLE | 2026-10-22 |
| `security` | `security.yml` | NOT_DEMONSTRABLE | 2026-10-22 |

`stable required status blocks merge on failure` is NOT_DEMONSTRABLE. Classic
branch protection is absent, and the rulesets that include `main` are
disabled, so a successful or failed `pr-gate-complete` does not by itself
block merge. Actions billing being restored does not turn that into server
enforcement.

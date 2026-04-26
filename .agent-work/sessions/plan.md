Problem
Audit and propose an optimization plan for GitHub settings in SatoryKono/BioactivityDataAcquisition with focus on CI/CD, code review, release process, and Git performance.

Approach
Review existing GitHub workflow configs and repository governance files, identify gaps (branch protection, required checks/reviews, release gating), and propose a staged optimization plan covering CI efficiency, review quality, and release reliability.

Todos
1) Assess branch protection and required checks/review policies for main (enable protections if missing).
2) Map and deduplicate CI workflows (tests, lint, type-checking, security) and improve trigger/path filters.
3) Optimize CI runtime (cache strategy alignment, matrix sizing, job consolidation, cancellation rules).
4) Harden security and dependency update flows (pip-audit gating, dependabot grouping/limits).
5) Improve code review governance (CODEOWNERS coverage, required reviewers, PR template enforcement).
6) Tighten release process (tag/release policy, environment protections, artifact retention).
7) Evaluate Git performance hygiene (repo size, LFS needs, GC settings, large file handling).

Notes
- Branch protection status is not visible via repo contents; needs confirmation in GitHub settings.
- Release workflow uses OIDC publishing to PyPI/TestPyPI; verify environment protections and required reviewers for release environments.

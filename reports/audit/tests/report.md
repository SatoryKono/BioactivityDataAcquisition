# Test-system audit — 2026-08-27

- Run: `20260827T101100Z-tests-new-26a28f462a`
- Base: `origin/main@9933fa425bd537e2ae615c9e29c9bee1c706a638`
- Scope: `tests/ configs/quality/ pyproject.toml`
- Audit mode: full; execution lane: canonical `unit-fast`
- Outcome: 3 PROVEN findings; 1 fixed locally; 3 cycle issues remain open.

## Executive result

The bounded lane is green before and after the fix: 21,613 tests, zero failures
and zero errors. The local correction converts one deterministic false-green
skip into an asserted pass, reducing skips from 20 to 19 without changing any
skip, xfail, coverage, or technical-debt budget.

The repository still has no enforced merge-blocking ruleset on `main`.
Ruleset 15730586 is disabled and classic branch protection is absent, so CI
workflow presence is not merge enforcement. Issue #9723 was reopened with
current live-API evidence.

Issue #9729 was also reopened after source re-attestation. Its acceptance
criteria remain unmet: serial-or-bounded lanes are invoked with xdist,
`tests/e2e` remains outside the reviewed skip census, and active non-critical
VCR mismatches still skip instead of failing closed.

## Findings

| ID | Requirement | P | State | Owner issue |
| --- | --- | --- | --- | --- |
| TEST-NEW-001 | REQ-TEST-005 | P1 | PROVEN, external blocker | #9723 |
| TEST-NEW-002 | REQ-TEST-005 | P2 | PROVEN, source drift | #9729 |
| TEST-NEW-003 | REQ-GOV-004 | P2 | PROVEN, fixed locally | #9751 |

## Command evidence

Baseline and retest used the same selector:

`python -m pytest tests/unit --ignore=tests/unit/scripts --ignore=tests/unit/repo_backed -m "not fs_contract and not repo_backed and not subprocess_backed and not slow and not benchmark and not memory" -q --tb=short`

| Evidence | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Baseline JUnit | 21613 | 0 | 0 | 20 |
| Retest JUnit | 21613 | 0 | 0 | 19 |
| Final rebased-SHA unit-fast | 21616 | 0 | 0 | 19 |
| ChEMBL helper file | 3 | 0 | 0 | 0 |
| Skip inventory governance | 12 | 0 | 0 | 0 |

Run-local XML and execution evidence live under
`reports/audit-runs/20260827T101100Z-tests-new-26a28f462a/` and are ignored
machine artifacts by repository policy.

## Residual risks and stop reason

- #9723 requires maintainer GitHub ruleset enablement. The audit did not mutate
  repository rules because the requested SCOPE does not authorize GitHub
  settings changes.
- #9729 spans CI/E2E surfaces outside the bounded unit fix and remains open.
- Optional dependency and OS-specific skips were observed but not classified as
  defects without CI/environment proof.
- No flaky test was claimed: the reviewed flaky inventory is empty and this run
  found a deterministic policy mismatch, not intermittent behavior.

The loop stops after one non-empty iteration because all in-scope bounded fixes
were exhausted and the remaining open cycle issues require external or broader
scope. Empty form cycles are not emitted.

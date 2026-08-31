# GitHub Actions cyclic audit final summary

## Result

**BLOCK** after 3 of 10 iterations. Early stop was reached because iterations 2 and 3 had no new PROVEN P0/P1 and no new in-scope regression. Open issues and non-green required CI prohibit PASS.

## Findings

1. P1 / REQ-DEP-002 / #9881: baseline temporary workflow granted contents:write, checked out refs/pull/9879/merge, executed local action and Python code, then committed and pushed. Evidence: lines 9, 18, 21, 35-38, 46-58.
2. P1 / GH-RULESET-001 / #9800: main is unprotected, ruleset 15730586 is disabled, and required contexts are empty.
3. P2 / REQ-DEP-002 / #9865: concurrency remediation exists, but final CI/evidence acceptance is open.

## Remediation and validation

- The dangerous workflow is absent on origin/main@7add6987645a81e973a579aa4cc5b6db6d32f1b5; catalog parity is 47/47.
- PR #9880 head 3421f7e8928e51da1e0bcb983d40a608634fcae1 adds the effective-permission-aware refs/pull regression guard; it is not accepted on main.
- Immutable pins: 232/232 baseline, 231/231 final. Artifact retention: 71/71. PR concurrency: 29/29. Cache surfaces: 7.
- Remote zizmor passed with a demonstrated baseline coverage gap.
- Local validation is DEGRADED because the Windows executor could not start.
- Required CI is not green; no merge or issue close was performed.

No secret was printed. No .env, debt budget, cap, threshold, exemption, ruleset, or admin-bypass mutation was made. No commit was made to main.

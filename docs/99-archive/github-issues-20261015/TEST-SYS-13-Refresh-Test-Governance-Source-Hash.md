---
title: "test(governance): refresh stale test-governance source tree hash"
labels:
  - testing
  - generated-artifact
  - governance
  - priority:P2
---

# Context

`reports/quality/test-governance-current.json` is a generated evidence artifact
checked against the tracked test source tree.

Iteration metadata: first observed in `CYCLE-02` at
`3910046d2716606019babc2a272bd64dc2d87982`.

# Problem

`scripts/engineering/qa/report_test_governance_audit.py --check` reports drift.
A temporary regeneration differs only in `source_tree_sha256`:

- committed: `e7a2a1234cbaa233958191255fe096b06241bf7aa9a908f4f70e4df806c07818`
- current: `ee8aedea9729d5930b90847a64347ae9c6ad7d74b819296a436ec547bf81567c`

Finding fingerprint:
`test-governance:committed-source-tree-sha256-stale`

# Evidence

- Executable evidence: generator `--check` exits nonzero.
- Generated diff evidence: all semantic counters and inventories are
  unchanged; only the source-tree hash differs.
- The targeted architecture governance tests remain green.

# Root Cause

Tracked test-source changes landed without refreshing the coupled generated
test-governance artifact.

# Architecture Impact

No runtime architecture invariant is broken, but the executable governance gate
cannot certify that committed evidence belongs to the current test tree.

# Proposed Remediation

Regenerate the artifact with the canonical QA command after confirming the
source change is intentional. Preserve all zero-ratchets and budgets.

# Rejected Approaches

- Do not disable the hash check.
- Do not exclude changed tests from the source fingerprint.
- Do not increase any governance budget.

# Acceptance Criteria

- Generator `--check` passes.
- Semantic counters do not regress.
- `refined_assertless_tests` remains zero.
- Relevant architecture tests pass.

# Verification

- `python scripts/engineering/qa/report_test_governance_audit.py --check`
- `pytest tests/architecture/test_test_governance_audit.py`
- Review the generated diff for hash-only or justified semantic changes.

# Risks and Rollback

An unintended semantic counter change would indicate a real test-governance
regression and must not be hidden by regeneration.

# Definition of Done

The committed artifact matches the generator, all ratchets remain equal or
better, and no thresholds or exemptions increase.

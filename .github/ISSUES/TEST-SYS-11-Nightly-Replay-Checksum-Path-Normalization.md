---
title: "test(ci): normalize nightly replay parity checksums by relative path"
labels:
  - testing
  - ci
  - determinism
  - priority:P1
---

# Context

The scheduled `nightly-replay-parity` workflow runs the determinism suite twice
under isolated `run1` and `run2` basetemp roots and compares checksums.

Iteration metadata: `CYCLE-01..CYCLE-05`, first observed at
`3910046d2716606019babc2a272bd64dc2d87982`.

# Problem

`.github/workflows/nightly-replay-parity.yml:53-55` hashes files using paths
that include the run-specific root and diffs the complete `sha256sum` output.
Identical content therefore produces different lines solely because one path
contains `run1` and the other contains `run2`.

Finding fingerprint:
`ci:replay-parity-checksum-compares-absolute-run-specific-paths`

# Evidence

- Code inspection: `.github/workflows/nightly-replay-parity.yml:43-55`.
- Test evidence:
  `tests/integration/determinism/test_reproducibility_determinism_gate.py:139-175`
  writes replay evidence below each pytest basetemp.
- Reproducer: two identical one-file trees below different `run1`/`run2`
  roots produce `diff exit 1`; the only changed text is the pathname.

# Root Cause

The workflow treats `sha256sum`'s presentation format
`<digest><spaces><input path>` as a canonical replay manifest. Input paths are
run-local identities, not semantic artifact identities.

# Architecture Impact

The false-negative scheduled gate reduces trust in BioETL determinism and
replay evidence. It does not alter runtime replay behavior, but it makes the
quality signal unreliable.

# Proposed Remediation

Generate manifests from within each run root and compare stable relative paths
plus content digests. Add a regression test for identical trees at different
roots and a negative case for changed content.

# Rejected Approaches

- Do not remove the parity comparison.
- Do not ignore `diff` failures.
- Do not compare only aggregate directory hashes without retaining
  file-level diagnostic evidence.

# Acceptance Criteria

- Equal trees under different roots compare equal.
- A path addition/removal or content mutation compares unequal.
- Manifest ordering is deterministic.
- Uploaded checksum artifacts remain human-diagnosable.

# Verification

- Targeted checksum helper unit test.
- `tests/integration/determinism` executed twice with isolated basetemps.
- Relevant architecture/workflow governance tests.
- YAML/action syntax validation.

# Risks and Rollback

Risk is limited to workflow evidence generation. Roll back to the previous
workflow step if normalized manifests omit files or become nondeterministic.

# Definition of Done

The workflow compares canonical relative-path manifests, regression tests cover
equal and unequal trees, relevant gates pass, and no determinism control is
weakened.

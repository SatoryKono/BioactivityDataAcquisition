______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-11-07'

______________________________________________________________________

# ADR-063: Exclude Generated Artifact Tests from GitHub Actions

## **Date:** 2026-11-07 **Status:** Accepted **Decision makers:** Repository Owner **Related:** ADR-042 (Testing Strategy Matrix)

## Context

Committed generated artifacts (telemetry baseline, governance artifacts, inventories, dependency maps, passports, manifests) are verified in CI by identity/freshness tests. Their drift systematically causes false-red PRs and Nightly builds for reasons unrelated to code changes. A textbook example is `source_tree_sha256` in the telemetry baseline: any PR modifying test inputs is forced to re-bind the baseline of unrelated data. This noise masks real failures and makes every acceptance more expensive.

## Decision

A group of tests whose subject is a generated artifact (criterion: the test verifies the content/hash of a generated file as its subject, rather than using it as a fixture) is isolated. This group is marked with a single pytest marker and a registry in `configs/quality/test_matrix.yaml`, and is excluded from all GitHub Actions runs using a single mechanism at the test matrix level. The tests themselves are preserved and can be run locally with a single command. New tests of this nature are included in the group upon creation.

## Alternatives Considered

- **Keep in CI with auto-regeneration:** Masks drift and generates commit churn. Rejected.
- **skip/xfail:** Silent exclusion without a registry. Rejected.
- **Delete the tests:** Loses local verification capability. Rejected.

## Consequences

### Positive
- Clean CI signal for code.
- Acceptance is not blocked by unrelated drift.

### Negative & Risks
- Drift of generated artifacts no longer blocks merges.
- Silent desynchronization of artifacts is possible.

### Mitigations
- Local/pre-release execution of the group is the responsibility of the artifact modifier.
- The group's registry serves as a single point of control.
- The decision will be reviewed when deterministic regeneration in CI becomes available.

### Coverage Impact
- The excluded group is not included in Actions coverage; the delta is shown explicitly.

## Related ADRs

- Implementation: This decision is implemented in a separate session/PR ("СРОЧНО: правило — тесты генерируемых артефактов исключаются из GitHub Actions").
- [ADR-042](ADR-042-testing-strategy-matrix.md): Testing Strategy Matrix and Fixture Governance. This ADR supplements ADR-042 by redefining the execution environment for generated artifact tests.

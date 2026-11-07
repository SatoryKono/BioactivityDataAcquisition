______________________________________________________________________

Version: 1.0.1
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

A group of tests whose subject is a generated artifact (criterion: the test verifies the content/hash of a generated file as its subject, rather than using it as a fixture) is isolated. This group is marked with a single pytest marker and a registry in `configs/quality/test_matrix.yaml`, and is to be excluded from all GitHub Actions runs using a single mechanism at the test matrix level. This is the target decision, not a claim that the migration is complete. The tests themselves are preserved and can be run locally with a single command. New tests of this nature are included in the group upon creation.

### Implementation Status

The current configuration in `configs/quality/test_matrix.yaml` excludes the group from ordinary CI through `ordinary_ci_selection: ci`. It still runs daily in `.github/workflows/nightly.yml` through the `generated-artifact-daily` job and `daily_selection: daily` (including slow tests). Exclusion from Nightly remains part of the separate implementation PR; this documentation PR does not change the workflow or matrix. Until that implementation lands, generated-artifact drift can still fail Nightly.

## Alternatives Considered

- **Keep in CI with auto-regeneration:** Masks drift and generates commit churn. Rejected.
- **skip/xfail:** Silent exclusion without a registry. Rejected.
- **Delete the tests:** Loses local verification capability. Rejected.

## Consequences

The following consequences describe the completed target state. The Nightly exception above remains in effect until the separate implementation lands.

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
- Once the target exclusion is implemented, the group will not be included in Actions coverage; the implementation must show the delta explicitly. The current daily Nightly execution remains unchanged by this ADR.

## Related ADRs

- Implementation: Completion of this decision, including exclusion from Nightly, is deferred to a separate session/PR ("СРОЧНО: правило — тесты генерируемых артефактов исключаются из GitHub Actions").
- [ADR-042](ADR-042-testing-strategy-matrix.md): Testing Strategy Matrix and Fixture Governance. This ADR supplements ADR-042 by redefining the execution environment for generated artifact tests.

______________________________________________________________________

Version: 1.0.1
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-21'

______________________________________________________________________

# ADR-042: Testing Strategy Matrix and Fixture Governance

## **Date:** 2026-03-09 **Status:** Accepted **Decision makers:** @BioETL-Team **Related:** ADR-027 (DQ rules), ADR-032 (HTTP unification), RULES.md §4

## Context

BioETL has grown to 854+ test files across 9 test categories. While coverage meets
the 85% threshold, several gaps exist:

1. **No formalized test matrix** — no systematic mapping of provider x entity x test type
1. **Fixture management** — VCR cassettes require canonical metadata,
   catalog validation, and stale-age checks
1. **Property-based testing** limited to domain layer; transformers lack property tests
1. **Mutation testing** exists in CI, with `domain/` and curated
   application control-plane targets currently blocking
1. **Contract tests** exist but no schema stability verification across versions
1. **Performance tests** optional, no regression gate

### Conflict: Property-Based Tests vs VCR Cassettes

Hypothesis generates random inputs, but VCR returns fixed recorded responses.
These are fundamentally incompatible at the adapter level. Clear boundary needed.

______________________________________________________________________

## Decision

### Test Matrix (Provider x Layer x Type)

| Layer                                  | Unit   | Integration | Contract | Property              | E2E    |
| -------------------------------------- | ------ | ----------- | -------- | --------------------- | ------ |
| **Domain** (ports, entities, policies) | MUST   | —           | —        | SHOULD                | —      |
| **Application** (pipelines, services)  | MUST   | SHOULD      | —        | SHOULD (transformers) | —      |
| **Infrastructure** (adapters, storage) | MUST   | MUST (VCR)  | MUST     | —                     | SHOULD |
| **Composition** (factories, wiring)    | SHOULD | SHOULD      | —        | —                     | MUST   |
| **Interfaces** (CLI)                   | SHOULD | —           | —        | —                     | MUST   |

### Property-Based Testing Boundary

- **Use Hypothesis FOR**: domain value objects, transformers, normalization logic,
  schema validators, content_hash computation, date parsing
- **NEVER use Hypothesis FOR**: HTTP adapter tests (use VCR instead),
  storage write tests (use fixtures), CLI integration tests

### Fixture Governance

1. VCR cassettes MUST live in `tests/fixtures/vcr/{provider}/`
1. Cassette metadata rollout is enforced: `_meta.yaml` sidecars are required
   for the managed VCR inventory declared in `configs/quality/test_matrix.yaml`
1. Stale cassettes (>90 days) are a blocking threshold for the managed inventory;
   CI validates sidecar age through the canonical VCR metadata checker
1. A canonical cassette-metadata catalog now lives at
   `reports/quality/vcr-metadata-catalog.json`; catalog drift is blocking
   through `python -m scripts.engineering.qa report-vcr-metadata --check`
1. Canonical tooling paths are active for enforced rollout at
   `scripts/engineering/qa/report_vcr_metadata_catalog.py` and
   `scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py`
1. Golden master snapshots for transformers live in `tests/fixtures/golden/{provider}/`
   with partial rollout allowed while provider coverage is still being expanded
1. Root-level / legacy cassette placement is already enforced in CI
1. Extensionless cassette filenames remain on a shrinking allowlist during gradual migration to `*.yaml`

### Mutation Testing Gate

- `mutmut` runs in CI for the `domain/` layer with a 70% blocking threshold
- A curated `src/bioetl/application/services/control_plane/` target now runs
  against `tests/unit/application/services/control_plane/` with a 60% blocking
  threshold
- broad `application/` mutation testing remains a staged target with a
  documented 60% threshold but is not yet a blocking CI gate
- zero-mutant, failed `mutmut results`, or unparseable mutation result output are
  workflow failures rather than informational skips, so active gates cannot pass
  silently
- Infrastructure layer excluded (I/O-heavy, low mutation value)

### Coverage Inventory

- The canonical coverage lane remains `coverage-verify`
- `coverage-verify` emits `reports/coverage/coverage.xml`
- `scripts/engineering/qa/report_module_coverage_inventory.py` converts the
  coverage XML into the committed module-level inventory at
  `reports/quality/module-coverage-inventory.json`
- The inventory must cover every `src/bioetl/**/*.py` module and explicitly
  classify each module as measured, partially covered, uncovered, unmeasured, or
  generated without coverage XML

### Contract Test Versioning

- Current schema-stability snapshots live in `tests/contract/silver_schemas/snapshots/`
- Externalized contract snapshot path is reserved at `tests/fixtures/contracts/{provider}/v{N}.json`
- Backward-compatibility snapshot enforcement on the externalized registry is staged until that inventory exists
- Breaking changes require explicit version bump with migration note once snapshot rollout is enabled
- Live provider contract verification remains active today via the scheduled
  `contract-tests.yml` workflow and must opt into outbound network access explicitly

### Live Provider Tiering

- `enforced`: provider is part of the minimum live contract baseline and must
  keep a dedicated `tests/contract/test_<provider>_contract.py` suite
- `pilot`: provider has an explicitly tracked live contract pilot suite, but is
  not yet part of the enforced minimum baseline
- `vcr_only`: provider confidence is currently carried through VCR-backed tests
  and must not silently grow a live contract suite without matrix promotion

______________________________________________________________________

## Consequences

### Positive

- Systematic coverage tracking via matrix
- Clear boundary between property-based and VCR testing
- Mutation testing catches undertested logic
- Contract versioning prevents silent schema breaks

### Negative

- Mutation testing adds ~5min to CI
- Fixture governance requires cassette metadata maintenance, catalog sync, and
  stale-age compliance for the managed inventory
- Property test generators need careful domain modeling

### Risks

- **Hypothesis + VCR conflict**: Mitigated by strict boundary (domain-only for property tests)
- **Mutation score flapping**: Mitigated by excluding I/O layer and using minimum thresholds

______________________________________________________________________

## Compliance

- RULES.md §4.2: TEST-001 (coverage), TEST-003 (VCR), TEST-004 (arch tests)
- This ADR extends RULES.md testing requirements with matrix governance

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.

## References

- `<link-or-path>`

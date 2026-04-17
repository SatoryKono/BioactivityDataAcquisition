---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-30'
---

# ADR-042: Testing Strategy Matrix and Fixture Governance

**Date:** 2026-03-09
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-027 (DQ rules), ADR-032 (HTTP unification), RULES.md §4
---

## Context

BioETL has grown to 854+ test files across 9 test categories. While coverage meets
the 85% threshold, several gaps exist:

1. **No formalized test matrix** — no systematic mapping of provider x entity x test type
2. **Fixture management** — VCR cassettes scattered without catalog or validation
3. **Property-based testing** limited to domain layer; transformers lack property tests
4. **Mutation testing** configured but not gated in CI (mutmut)
5. **Contract tests** exist but no schema stability verification across versions
6. **Performance tests** optional, no regression gate

### Conflict: Property-Based Tests vs VCR Cassettes

Hypothesis generates random inputs, but VCR returns fixed recorded responses.
These are fundamentally incompatible at the adapter level. Clear boundary needed.

---

## Decision

### Test Matrix (Provider x Layer x Type)

| Layer | Unit | Integration | Contract | Property | E2E |
|-------|------|-------------|----------|----------|-----|
| **Domain** (ports, entities, policies) | MUST | — | — | SHOULD | — |
| **Application** (pipelines, services) | MUST | SHOULD | — | SHOULD (transformers) | — |
| **Infrastructure** (adapters, storage) | MUST | MUST (VCR) | MUST | — | SHOULD |
| **Composition** (factories, wiring) | SHOULD | SHOULD | — | — | MUST |
| **Interfaces** (CLI) | SHOULD | — | — | — | MUST |

### Property-Based Testing Boundary

- **Use Hypothesis FOR**: domain value objects, transformers, normalization logic,
  schema validators, content_hash computation, date parsing
- **NEVER use Hypothesis FOR**: HTTP adapter tests (use VCR instead),
  storage write tests (use fixtures), CLI integration tests

### Fixture Governance

1. VCR cassettes MUST live in `tests/fixtures/vcr/{provider}/`
2. Cassette metadata rollout is staged in `partial` mode: `_meta.yaml` sidecars are
   now present for a seeded inventory, but CI enforcement is not yet repo-wide
3. Stale cassettes (>90 days) remain a configured target threshold, and rollout is now
   `partial`: metadata inventory exists, but stale-age enforcement is not yet a full
   blocking CI gate for the entire cassette estate
4. A canonical cassette-metadata catalog now lives at
   `reports/quality/vcr-metadata-catalog.json`; generation exists, but coverage and
   workflow automation are still partial
5. Canonical tooling paths are active for partial rollout at
   `scripts/engineering/qa/report_vcr_metadata_catalog.py` and
   `scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py`; workflow-level
   automation can remain staged even after the tooling exists
6. Golden master snapshots for transformers live in `tests/fixtures/golden/{provider}/`
   with partial rollout allowed while provider coverage is still being expanded
7. Root-level / legacy cassette placement is already enforced in CI
8. Extensionless cassette filenames remain on a shrinking allowlist during gradual migration to `*.yaml`

### Mutation Testing Gate

- `mutmut` runs in CI today for the `domain/` layer with a 70% blocking threshold
- `application/` mutation testing remains a staged target with a documented 60% threshold
  but is not yet a blocking CI gate
- Infrastructure layer excluded (I/O-heavy, low mutation value)

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

---

## Consequences

### Positive
- Systematic coverage tracking via matrix
- Clear boundary between property-based and VCR testing
- Mutation testing catches undertested logic
- Contract versioning prevents silent schema breaks

### Negative
- Mutation testing adds ~5min to CI
- Fixture governance requires cassette metadata maintenance, an initial backfill, and a
  later stale-age gate once that metadata inventory exists
- Property test generators need careful domain modeling

### Risks
- **Hypothesis + VCR conflict**: Mitigated by strict boundary (domain-only for property tests)
- **Mutation score flapping**: Mitigated by excluding I/O layer and using minimum thresholds

---

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

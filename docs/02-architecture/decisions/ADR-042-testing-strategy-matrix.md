# ADR-042: Testing Strategy Matrix and Fixture Governance

**Status:** Accepted
**Date:** 2026-03-09
**Authors:** Claude (architecture review)
**Supersedes:** —
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
2. Each cassette MUST have a corresponding `_meta.yaml` with recording date and API version
3. Stale cassettes (>90 days) SHOULD be flagged in CI
4. Golden master snapshots for transformers stored in `tests/fixtures/golden/{provider}/`

### Mutation Testing Gate

- `mutmut` MUST run on `domain/` and `application/` layers in CI
- Minimum mutation score: 70% (domain), 60% (application)
- Infrastructure layer excluded (I/O-heavy, low mutation value)

### Contract Test Versioning

- Schema snapshots stored in `tests/fixtures/contracts/{provider}/v{N}.json`
- Contract tests verify backward compatibility across versions
- Breaking changes require explicit version bump with migration note

---

## Consequences

### Positive
- Systematic coverage tracking via matrix
- Clear boundary between property-based and VCR testing
- Mutation testing catches undertested logic
- Contract versioning prevents silent schema breaks

### Negative
- Mutation testing adds ~5min to CI
- Fixture governance requires cassette metadata maintenance
- Property test generators need careful domain modeling

### Risks
- **Hypothesis + VCR conflict**: Mitigated by strict boundary (domain-only for property tests)
- **Mutation score flapping**: Mitigated by excluding I/O layer and using minimum thresholds

---

## Compliance

- RULES.md §4.2: TEST-001 (coverage), TEST-003 (VCR), TEST-004 (arch tests)
- This ADR extends RULES.md testing requirements with matrix governance

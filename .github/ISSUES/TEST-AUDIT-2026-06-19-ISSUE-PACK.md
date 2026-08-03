# Test System Audit 2026-06-19 Issue Pack

This pack converts the validated 2026-06-19 test-system audit into a
publish-ready GitHub issue set.

## Scope

The pack covers only findings that were re-verified on the current repository
state:

- weak / duplicate observability test coverage in the root infrastructure test file
- blurred pure-unit vs repo-backed-unit boundaries
- E2E metadata drift against Local-Only runtime reality
- duplication visibility blind spots for fixtures / VCR / golden artifacts
- contract-oriented unit test naming drift
- missing narrow maintenance-path fidelity coverage outside E2E
- incomplete branch-consumable test telemetry for snapshot-based audits

## Issue Set

1. `TEST-AUDIT-001` — trim legacy root observability test surface — [#5423](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5423)
2. `TEST-AUDIT-002` — separate repo-backed tests from canonical pure-unit lanes — [#5424](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5424)
3. `TEST-AUDIT-003` — align E2E metadata with Local-Only runtime — [#5426](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5426)
4. `TEST-AUDIT-004` — add duplication visibility for fixtures / VCR / golden — [#5428](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5428)
5. `TEST-AUDIT-005` — consolidate contract-oriented unit test taxonomy — [#5430](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5430)
6. `TEST-AUDIT-006` — add integration coverage for cleanup / compaction semantics — [#5432](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5432)
7. `TEST-AUDIT-007` — publish branch-consumable test telemetry summaries — [#5434](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5434)

## Recommended Execution Order

### Phase 1: low-risk cleanup

1. `TEST-AUDIT-001`
2. `TEST-AUDIT-003`
3. `TEST-AUDIT-005`

### Phase 2: boundary clarification

4. `TEST-AUDIT-002`

### Phase 3: governance and fidelity

5. `TEST-AUDIT-004`
6. `TEST-AUDIT-006`
7. `TEST-AUDIT-007`

## Notes

- This pack intentionally does **not** restate already-governed fixture
  freshness controls as missing functionality.
- This pack intentionally does **not** claim that coverage is wholly
  immeasurable from the repository snapshot; committed coverage artifacts are
  present, while slow-test summaries are the main missing snapshot surface.

# AUDIT-016: Prepare ADR spike for checkpoint versus ledger-based resume

## 1. Title
[governance] Prepare ADR spike for checkpoint versus ledger-based resume

## 2. Problem
The project has checkpoint-based operational resume and RunManifest/RunLedger-based provenance/inspection. There is an open design question about whether resume should remain checkpoint-based or move to ledger replay. No implementation decision should be made without an ADR-level spike.

## 3. Evidence
- `src/bioetl/application/composite/checkpoint/service.py::CompositeCheckpointService`
- `src/bioetl/application/composite/checkpoint/load_service.py::CompositeCheckpointLoadService`
- `src/bioetl/application/composite/checkpoint/state.py::CompositeCheckpointState`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/application/services/control_plane/run_ledger_service.py`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
  - Lines 182-196 describe current resume model: "composite resume uses checkpoint snapshot state as the base and then replays ledger entries strictly after last_event_id"
  - ADR states: "ADR-044 therefore does not require one universal replay algorithm across all runner families"
- `docs/05-operations/runbooks/run-manifest-inspection.md`
- `src/bioetl/interfaces/cli/commands/domains/run_manifest/...`

## 4. Root Cause
Design boundary ambiguity between operational resumable state and provenance/inspection ledger.

## 5. Architectural Impact
- Determinism / replay: ledger replay could change resume semantics and failure recovery
- Idempotency: offset reconstruction and batch boundaries must remain deterministic
- Layer boundaries: ledger storage and checkpoint ports must not be mixed casually
- Observability: RunLedger is currently an inspection/control-plane surface; making it operational state changes its role
- Reproducibility: exact replay requirements must stay aligned with Bronze snapshots and manifest identity

## 6. Required Outcome
A short ADR spike or technical design note must answer:
- keep checkpoint as operational state and ledger as provenance
- move resume to ledger replay
- hybrid model
- not now / never recommendation

No production code change is required for this issue.

## 7. File-level Implementation Plan
### Changes
- `docs/02-architecture/decisions/ADR-0XX-checkpoint-vs-ledger-resume.md`
  - Add ADR spike or design note
  - Include current model:
    - checkpoint state
    - checkpoint compatibility policy
    - manifest/ledger inspection path
    - composite checkpoint behavior
  - Include comparison matrix:
    - checkpoint operational state
    - ledger resumable execution state
    - hybrid model
  - Include risk assessment:
    - partial failure
    - batch boundary reconstruction
    - destructive replay
    - local-only assumptions
    - exact replay limits
  - Include recommendation

- `docs/05-operations/runbooks/run-manifest-inspection.md`
  - Add a short note if the ADR clarifies that ledger is not operational resume state

- `docs/00-project/00-map.md`
  - Add ADR link only if the design note becomes accepted/active

### Refactoring actions
- None. This is a governance/design issue
- No production code edits

### Contracts impact
- ADR/control-plane documentation only
- No port changes
- No schema changes
- No config contract changes

### Migration
- No data migration

## 8. Constraints
Forbidden:
- implementing ledger-based resume in this issue
- changing checkpoint semantics
- changing RunManifest / RunLedger contract
- adding I/O to domain
- importing infrastructure into domain
- weakening Gold strict validation
- changing Quarantine payload
- adding speculative TODOs without evidence

## 9. Acceptance Criteria
- ADR/design note exists with evidence-based current-state analysis
- It explicitly compares checkpoint-based resume versus ledger replay
- It documents recommendation: recommended now, not now, or never
- It lists required migration work if ledger resume is ever selected
- Docs checks pass
- No production code changed except optional docs references
- No dependency cycles, because no code moved

## 10. Priority
P2. This prevents an expensive architectural rewrite based on vibes, which is apparently still a popular methodology.

## 11. Size
S. Documentation-only spike.

## 12. Labels
governance, architecture

## 13. Dependencies
Should be completed before any implementation issue that attempts ledger-based resume.

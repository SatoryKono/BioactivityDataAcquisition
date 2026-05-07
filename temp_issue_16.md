## Problem

The project has checkpoint-based operational resume and RunManifest/RunLedger-based provenance/inspection. There is an open design question about whether resume should remain checkpoint-based or move to ledger replay. No implementation decision should be made without an ADR-level spike.

ADR-044 mentions checkpoint vs ledger resume (lines 182-200) but does not provide a clear design decision or comparison matrix.

## Evidence

- `src/bioetl/application/composite/checkpoint/service.py::CompositeCheckpointService`
- `src/bioetl/application/composite/checkpoint/load_service.py::CompositeCheckpointLoadService`
- `src/bioetl/application/composite/checkpoint/state.py::CompositeCheckpointState`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/application/services/control_plane/run_ledger_service.py`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md` (lines 182-200 mention resume but lack clear decision)
- `docs/05-operations/runbooks/run-manifest-inspection.md`
- `src/bioetl/interfaces/cli/commands/domains/run_manifest/...`

## Root Cause

Design boundary ambiguity between operational resumable state and provenance/inspection ledger.

## Architectural Impact

- Determinism / replay: Ledger replay could change resume semantics and failure recovery
- Idempotency: Offset reconstruction and batch boundaries must remain deterministic
- Layer boundaries: Ledger storage and checkpoint ports must not be mixed casually
- Observability: RunLedger is currently an inspection/control-plane surface; making it operational state changes its role
- Reproducibility: Exact replay requirements must stay aligned with Bronze snapshots and manifest identity

## Required Outcome

A short ADR spike or technical design note must answer:
- Keep checkpoint as operational state and ledger as provenance
- Move resume to ledger replay
- Hybrid model
- Not now / never recommendation

No production code change is required for this issue.

## Implementation Plan

Create `docs/02-architecture/decisions/ADR-0XX-checkpoint-vs-ledger-resume.md` with:

1. Current model analysis:
   - Checkpoint state
   - Checkpoint compatibility policy
   - Manifest/ledger inspection path
   - Composite checkpoint behavior

2. Comparison matrix:
   - Checkpoint operational state
   - Ledger resumable execution state
   - Hybrid model

3. Risk assessment:
   - Partial failure
   - Batch boundary reconstruction
   - Destructive replay
   - Local-only assumptions
   - Exact replay limits

4. Recommendation with rationale

5. If ledger resume is selected, list required migration work

6. Update `docs/05-operations/runbooks/run-manifest-inspection.md` if ADR clarifies ledger role

7. Add ADR link to `docs/00-project/00-map.md` if design note becomes accepted/active

## Acceptance Criteria

- ADR/design note exists with evidence-based current-state analysis
- Explicitly compares checkpoint-based resume versus ledger replay
- Documents recommendation: recommended now, not now, or never
- Lists required migration work if ledger resume is ever selected
- Docs checks pass
- No production code changed except optional docs references
- No dependency cycles (no code moved)

## Priority

P2 - This prevents an expensive architectural rewrite based on vibes

## Size

S - Documentation-only spike

## Labels

governance, architecture

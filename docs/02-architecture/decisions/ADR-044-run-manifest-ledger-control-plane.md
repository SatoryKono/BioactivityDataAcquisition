# ADR-044: Run Manifest and Run Ledger Control Plane

**Status:** Accepted
**Date:** 2026-03-24
**Decision makers:** @BioETL-Team
**Related:** ADR-014 (deterministic writes), ADR-015 (pipeline lifecycle), ADR-029 (output metadata), ADR-043 (documentation governance)

## Context

BioETL already captured useful provenance fragments during execution:

- `RunContext` stored `pipeline_version`, `git_commit`, and `config_hash`
- Bronze/Silver/Gold sidecars stored runtime and lineage metadata
- `PipelineRun` modeled in-process lifecycle transitions

However, those facts were distributed across multiple layers and were not
persisted as one immutable control-plane artifact. As a result, reproducibility
remained partial:

- a run could be identified by `run_id`, but not by one canonical manifest;
- incident/debug workflows had to reconstruct provenance from logs and sidecars;
- it was hard to distinguish exact replay of the same resolved launch from a new
  run that happened to write to the same destinations.

## Decision

BioETL introduces a dedicated control-plane family with two different roles:

### 1. `RunManifest` is immutable

`RunManifest` captures what was intended to run:

- `manifest_id`
- `run_id`
- `execution_fingerprint`
- pipeline/provider/entity identity
- resolved runtime/config snapshot
- code provenance (`pipeline_version`, `git_commit`, `config_hash`)
- source references
- planned artifact references

The manifest is created and persisted **before** runner execution begins.

### 2. `RunLedgerEntry` is append-only

`RunLedgerEntry` records what actually happened during lifecycle:

- `manifest_created`
- `run_started`
- `run_finished`
- `run_failed`
- `run_shutdown`

Additional lineage-oriented events such as `artifact_published` may be added
later without mutating existing manifests.

### 3. `manifest_id` links execution-local projections

`RunContext`, `PipelineRunContext`, runtime sidecar metadata, and inspection CLI
carry `manifest_id` as a reference. They do **not** embed the full manifest.

### 4. File-backed persistence is the first implementation

The initial control-plane store is filesystem-backed:

- `data/output/control/run_manifest/{manifest_id}.json`
- `data/output/control/run_manifest/_by_run_id/{run_id}.txt`
- `data/output/control/run_ledger/{manifest_id}.jsonl`
- `data/output/control/run_ledger/_by_run_id/{run_id}.txt`

This keeps the domain/application contracts stable while leaving room for a
future SQLite/Delta projection.

### 5. Inspection is part of the supported CLI

The control plane is inspectable via:

- `bioetl run-manifest show <run-id|manifest-id>`
- `bioetl run-manifest diff <left> <right>`

### 6. Governance is fail-closed

The system follows the invariant:

`no manifest, no run`

At the verification level, canonical E2E full-cycle coverage must assert that a
successful pipeline run emits both manifest and ledger artifacts.

## Consequences

### Positive

1. Each run becomes a globally addressable reproducibility object.
2. Run-centric provenance can be inspected without reconstructing logs.
3. Sidecars now link upward to the control plane through `manifest_id`.
4. The model creates a stable base for future lineage and replay tooling.

### Negative

1. Additional control-plane files are written for every run.
2. Readers that only knew `run_id` must learn the `manifest_id` link.
3. File-backed inspection is simple but not optimized for large historical query workloads.

## Implementation Notes

### Canonical code locations

- `src/bioetl/domain/control_plane/`
- `src/bioetl/domain/ports/control_plane/`
- `src/bioetl/application/services/run_manifest_service.py`
- `src/bioetl/application/services/run_ledger_service.py`
- `src/bioetl/application/services/run_manifest_inspection_service.py`
- `src/bioetl/infrastructure/control_plane/`

### Execution boundary

Manifest creation is wired into the pipeline bootstrap/runtime assembly path
before runner execution. Ledger attachment happens during runner construction so
runtime lifecycle events are appended through one shared control-plane service.

## Compliance

- Reproducibility and deterministic execution: ADR-014
- Lifecycle boundaries and shutdown behavior: ADR-015
- Sidecar metadata linkage: ADR-029
- Documentation publication and runbook indexing: ADR-043

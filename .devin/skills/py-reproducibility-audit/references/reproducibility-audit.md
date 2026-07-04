# Reproducibility Audit Reference

## Audit Goal

Determine whether BioETL pipelines are reproducible as exact computational
acts, not just approximate reruns that usually produce similar outputs.

Base every conclusion on:

- current code
- current configs
- current tests
- current architecture docs and rules
- runtime/control-plane reproducibility artifacts already used by the project

Mandatory artifact surface:

- `run_id`
- `manifest_id`
- `execution_fingerprint`
- `config_hash`
- `effective_config_hash`
- `git_commit`
- `contract_ref`
- `contract_version`
- `content_hash`
- checkpoint state
- lineage / sidecar metadata

Treat manifest/ledger identity, execution fingerprint, and immutable
control-plane objects as the current baseline architecture.

## What To Check

### 1. Determinism

Verify whether identical input, config, code, runtime parameters, and ordering
produce identical outputs.

Look for:

- current-time dependence
- unstable ordering
- non-deterministic retries or jitter
- randomness
- external state not captured in runtime metadata
- unstable serialization before hash/fingerprint computation

### 2. Idempotency

Verify whether repeat execution avoids duplicates and avoids changing outputs
without true input/config/code changes.

Check:

- merge/upsert semantics
- business and primary keys
- `content_hash` policy
- exclusion of meta/runtime fields from hashes
- Silver/Gold write semantics
- replay/backfill/rebuild behavior
- partial-failure reruns

### 3. Run-Level Control Plane Reproducibility

Verify whether a run can be reconstructed unambiguously:

- what was planned
- what config was used
- what code and contracts were used
- what artifacts were produced
- how one run differs from another

Evaluate:

- RunManifest completeness
- execution fingerprint quality
- append-only ledger / lifecycle trace
- `run_id ↔ manifest_id ↔ artifacts` linkage
- exact replay metadata sufficiency
- any fail-closed invariant such as `no manifest, no run`

### 4. Checkpoint / Resume / Replay

Treat checkpointing as part of reproducibility.

Verify:

- whether resume is safe after interruption
- which identity anchors guard checkpoint compatibility
- whether incompatible config/contract changes are blocked
- whether checkpoint identity can drift from canonical run identity

### 5. Lineage And Sidecar Metadata

Verify whether Bronze/Silver/Gold metadata and sidecars are sufficient for:

- traceability
- forensic reconstruction
- exact replay
- diffing two runs

Distinguish:

- fields that are actually written
- fields that are only documented
- fields that drift across layers

## What Counts As A Problem

Treat the following as findings:

- missing canonical run identity
- drift between manifest identity, checkpoint identity, and artifact identity
- non-deterministic hashes or fingerprints
- runtime state that affects outputs but is not captured in metadata
- inability to distinguish exact replay from a logically new run
- missing code/config provenance
- incomplete or contradictory lineage metadata
- only partial idempotency
- replay implemented as a logically new run
- layer-boundary violations that scatter reproducibility control across layers

Mark as **critical** any defect that blocks exact reproducibility.

## Scoring

Score each category from `0` to `10`:

- `Determinism`
- `Idempotency`
- `Run Identity`
- `Checkpoint Safety`
- `Lineage Completeness`
- `Replay Readiness`
- `Layer Consistency`

Also provide one integral score.

## Mandatory Output Sections

Use exactly this section order:

1. `Executive Summary`
2. `Фактическая модель воспроизводимости в текущем main`
3. `Что уже реализовано хорошо`
4. `Основные проблемы`
5. `Матрица рисков`
6. `Количественная оценка`
7. `План исправлений P0 / P1 / P2`

## Remediation Plan Rules

For each remediation item include:

- problem
- why it harms reproducibility
- concrete files / modules / layers
- proposed fix
- priority:
  - `P0` blocks exact reproducibility
  - `P1` weakens reproducibility systemically
  - `P2` improves investigation quality
- `DoD`

## Guardrails

- Do not claim anything without code/doc evidence.
- Do not replace reproducibility analysis with generic observability analysis.
- Do not merge replay, resume, rebuild, and incremental semantics into one term.
- Do not propose infrastructure fixes inside the domain layer.
- Respect DDD / Hexagonal / Medallion / Composite constraints.
- `run_id` alone is never proof of reproducibility.

## Final Question

Answer explicitly:

`Можно ли по текущему состоянию проекта воспроизвести любой pipeline run как строго определённый вычислительный акт, а не как приблизительное повторение процесса?`

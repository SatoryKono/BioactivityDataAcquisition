# ADR-056: Proof-or-Stop lifecycle control

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** BioETL maintainers

## Context

BioETL already has comprehensive pre-commit, pre-push, CI, documentation,
architecture, and debt gates. It also has an immutable EvidenceStore. The
missing boundary is mechanical: an agent can describe work as done without one
source-bound gate proving that the evidence belongs to the current task and
repository state.

## Decision

Adopt the repository-local Proof-or-Stop contract in
`docs/04-reference/contracts/proof-or-stop-evidence.md`.

Agent output remains a claim. `tested`, `reviewed`, `done`, and
`ready_to_merge` lifecycle transitions require an evidence bundle admitted by
the offline verifier. The verifier returns `ADMIT`, `STOP`, or `DEGRADED` and
fails closed for unavailable, stale, incomplete, unauthorized, cross-scope, or
tampered evidence.

Existing QA tools remain authoritative for their own thresholds. Their reports
are normalized into source-bound receipts; Proof-or-Stop does not rerun them or
introduce a second debt budget. Local digest-only evidence is useful but cannot
qualify a full-trust merge claim. CI and independent evaluators may provide the
stronger execution identity required for `ADMIT`.

CI artifact assembly and durable EvidenceStore ingestion are separate. CI does
not append directly to durable JSONL storage. Ingestion requires explicit
read-write memory mode and actor identity and records evidence events only.
Gate failures never manufacture waivers or decisions.

Enforcement follows the governed `observe` → `soft_fail` → `hard_fail`
(blocking) sequence.
Promotion requires the adversarial pilot and clean soak evidence; rollback is
a stage change, not deletion or mutation of prior evidence.

## Consequences

- False `DONE`/`ADMIT` caused by stale or incomplete receipts becomes
  mechanically detectable.
- CI remains vendor-neutral and local-first; optional evaluators cannot
  override the core gate.
- Evidence bundles add small artifact and validation costs.
- Operational proof remains bounded by the checks selected in policy and must
  not be presented as proof of semantic correctness.

## Alternatives rejected

- Treat agent prose as lifecycle state: no integrity or freshness boundary.
- Make a vendor evaluator authoritative: weakens local-first operation and
  creates availability coupling.
- Append from every CI shard directly to EvidenceStore: unsafe concurrent
  mutation and unclear authorization.
- Auto-create decisions after failure: converts a stop into an unreviewed
  waiver.

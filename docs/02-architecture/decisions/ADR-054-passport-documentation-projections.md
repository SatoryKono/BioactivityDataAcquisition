# ADR-054: Evidence-backed passport documentation projections

**Status:** Accepted  
**Date:** 2026-07-29  
**Owners:** BioETL Team

## Context

BioETL has 22 registered entity pipelines, five composite pipelines, and 27
ADR-047 workflows. Existing reference pages are useful, but only
`chembl_activity` has a generated dataflow passport, and that generator is
pipeline-specific. Manually duplicating runtime facts across 54 pages would
create a second, drifting source of truth.

## Decision

BioETL publishes passports as deterministic, read-only documentation
projections:

1. `scripts/docs/passports/` discovers executable units from their canonical
   registration/config surfaces.
2. Generated JSON records facts, provenance, evidence references, and
   diagnostics. Versioned JSON Schemas define the published contract.
3. Optional manual sidecars may add purpose, rationale, limitations, and
   approved exceptions. They cannot override generated facts.
4. Human Markdown and diagram views are renderings of the same generated facts.
5. Runtime packages under `src/bioetl/**` never import passport tooling or
   generated passports.
6. Tracked output contains a source revision and semantic content hash, but no
   wall-clock timestamp, occurrence identity, local path, or secret value.
7. Dynamic facts are marked `runtime_resolved`, `conditional`, `unknown`, or
   `traceability_gap`; projectors do not guess values.
8. Metric labels and forensic correlation fields remain separate. Run and
   manifest identities are prohibited as Prometheus labels.

Schema changes use SemVer. Major versions are incompatible, minor versions are
additive, and patch versions clarify constraints without changing semantic
shape.

## Source precedence

Executable registration/discovery, effective validated config, Domain
contracts, Application execution semantics, and Infrastructure request
construction each remain authoritative for the facts they own. Tests and
published narrative are evidence, not replacements for executable owners.

## Consequences

- Completeness, orphan, source-reference, and deterministic drift become
  testable.
- Existing reference pages can be consolidated without making docs runtime
  dependencies.
- Partial knowledge remains honest through diagnostics.
- Projector code is additional tooling, but it reduces duplicated narrative and
  does not increase technical-debt budgets.

## Alternatives rejected

- Fully manual passports: untestable drift.
- Runtime-owned passport DTOs: reverses dependency direction.
- Marker-bounded generated blocks in narrative Markdown: fragile merging and
  mixed ownership.
- Separate cached-Bronze passports: duplicates one semantic pipeline identity.


______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-26'

______________________________________________________________________

# Composite Validation Layer

## Purpose

The composite validation layer defines how composite configuration checks are
separated and composed into operator-facing validation outcomes.

Primary implementation:

- `src/bioetl/domain/services/composite_validation_layer.py`

Supporting modules:

- `src/bioetl/domain/services/composite_validation_helpers.py`
- `src/bioetl/domain/services/aggregation_validator.py`
- `src/bioetl/domain/services/cross_validation_validator.py`

## Layer boundaries

### Structural layer

Validates fundamental config shape and required keys. Produces structural
issues (`ValidationLayer.STRUCTURAL`) when required elements are missing or
invalid.

### Deep preflight layer

Validates semantic correctness of composite behavior:

- aggregation semantics
- cross-validation policy/config semantics
- field priority consistency
- lineage configuration sufficiency

Produces issues under `ValidationLayer.DEEP_PREFLIGHT`.

### Governance decision layer

`PreflightGovernanceService` evaluates validation report severity/policy and
returns execution decision (block, allow, warn) according to governance config.

## Operational notes

- The layer intentionally separates issue production from execution decisioning.
- Cross-validation outcomes are expected to surface into diagnostics and
  traceability runbooks via downstream control-plane signals.

## Related docs

- [Composite Validation Service](composite-validation-service.md)
- [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md)
- [Traceability Signal Ownership](../../05-operations/runbooks/traceability-signal-ownership.md)

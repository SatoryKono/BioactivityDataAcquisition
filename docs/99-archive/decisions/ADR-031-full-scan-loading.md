# ADR-031: Full Scan Loading Strategy

**Status:** Superseded (Renamed)
**Date:** 2026-01-26
**Decision makers:** @BioETL-Team
**Superseded by:** [ADR-031: Loading Strategy Formalization](ADR-031-loading-strategy-formalization.md)
**Relates to:** ADR-030 (Publication Pagination Strategy), ADR-011 (Remove Watermark)

## Context

Legacy documentation described publication pipelines as "full-scan loading" without a
formal strategy model. This made it unclear why resume was blocked and how future
incremental strategies should be represented.

## Decision (Summary)

Formalize loading behavior via an explicit `LoadingStrategy` enum and keep
`full-scan-only` for publication pipelines. The boolean `force-full-scan` remains for
backward compatibility, but `loading-strategy` is the explicit source of truth.

See the canonical ADR for full details:
- [ADR-031: Loading Strategy Formalization](ADR-031-loading-strategy-formalization.md)

## Consequences (Summary)

### Positive
- Explicit, self-documenting loading semantics in configs
- Extensible for future strategies (watermark-based)

### Negative
- Migration effort for existing configs
- Temporary dual-field configuration (`force-full-scan` + `loading-strategy`)

## Notes

This file preserves the legacy ADR name used in older docs. Use ADR-031
(Loading Strategy Formalization) for the full decision and implementation plan.

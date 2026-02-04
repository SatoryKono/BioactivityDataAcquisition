# ADR-030: OpenAlex Offset Stability

**Status:** Superseded (Renamed)
**Date:** 2026-01-26
**Decision makers:** @BioETL-Team
**Superseded by:** [ADR-030: Publication Pagination Strategy](ADR-030-publication-pagination-strategy.md)
**Relates to:** ADR-009 (Paginated Fetcher Mixin), ADR-011 (Remove Watermark)

## Context

OpenAlex publication data changes frequently (metadata updates, merges, and ID corrections).
Offset-based resume is not safe because record order can shift between runs, producing
skips and duplicates.

## Decision (Summary)

Treat OpenAlex publication pipelines as **full-scan only** and disable checkpoint resume.
Deduplication occurs in Silver via `content_hash`.

Full details and cross-provider context are documented in:
- [ADR-030: Publication Pagination Strategy](ADR-030-publication-pagination-strategy.md)

## Consequences (Summary)

### Positive
- Stable, deterministic snapshots per run
- No data loss due to offset drift

### Negative
- Higher API usage and longer execution time
- Restart required after interruption

## Notes

This file preserves the legacy ADR name used in older docs. Use the canonical ADR-030
for implementation and config specifics.

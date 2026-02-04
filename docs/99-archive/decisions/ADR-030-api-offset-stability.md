# ADR-030: API Offset Stability

**Status:** Superseded (Renamed)
**Date:** 2026-01-26
**Decision makers:** @BioETL-Team
**Superseded by:** [ADR-030: Publication Pagination Strategy](ADR-030-publication-pagination-strategy.md)
**Relates to:** ADR-009 (Paginated Fetcher Mixin), ADR-011 (Remove Watermark)

## Context

This ADR name was used in early documentation to describe a core issue:
offset-based pagination is **unstable** for publication APIs that update frequently.
Resume from offset can lead to **skipped records** and **duplicates** after upstream data shifts.

This affected publication pipelines across providers (ChEMBL, PubMed, CrossRef, OpenAlex, Semantic Scholar).

## Decision (Summary)

Adopt a **full-scan strategy** for publication pipelines and explicitly block
checkpoint-based resume. Deduplication is handled in Silver using `content_hash`.

The canonical, detailed decision record is:
- [ADR-030: Publication Pagination Strategy](ADR-030-publication-pagination-strategy.md)

## Consequences (Summary)

### Positive
- No data loss from offset shifts
- Reproducible, idempotent full scans

### Negative
- Longer runtimes and higher API load
- No mid-run resume (restart from offset 0)

## Notes

This ADR exists to preserve legacy links. Use ADR-030 (Publication Pagination Strategy)
for the full decision and implementation details.

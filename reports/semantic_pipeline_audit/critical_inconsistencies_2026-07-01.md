# Semantic Pipeline Critical Inconsistencies

Generated: `2026-07-01`

## Summary

- CRITICAL: `0`
- HIGH: `1`
- MEDIUM: `0`
- LOW: `3244`

## CRITICAL And HIGH Rows

| Risk | Cluster | Pipeline A | Field A | Pipeline B | Field B | Normalization | Validation | Typing | Row Key |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH | shared_corpus_id | composite_publication | corpus_id | semanticscholar_publication | corpus_id | COMPATIBLE | COMPATIBLE | CONFLICTING | 5273e9414bfd0017 |

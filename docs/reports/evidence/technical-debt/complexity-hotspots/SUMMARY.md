# Complexity Hotspots — Summary

Status: active
Rebaseline: Historical trigger evidence collected.

## Scope

Complexity hotspots identified via radon CC analysis across `src/`.

## Key Findings

- Adapter modules (ChEMBL, PubMed, CrossRef, UniProt, PubChem) carry justified
  complexity from retry/fallback logic.
- `batch_executor.py` CC is governed by a dedicated xenon gate.
- Memory graph importers (`src/memory/graph/`) are excluded from strict CC
  checks due to complex record iteration patterns.

Freshness note: rebaseline when new adapter modules exceed CC thresholds.

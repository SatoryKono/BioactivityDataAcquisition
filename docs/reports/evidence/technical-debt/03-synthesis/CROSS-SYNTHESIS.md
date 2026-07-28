# Technical Debt — Cross-Synthesis

Status: active
Rebaseline: Historical trigger evidence confirms current debt surfaces are tracked.

## Synthesis

Technical debt items are tracked through:

1. **Complexity hotspots** — radon CC violations in adapter and pipeline code.
1. **Duplication surfaces** — jscpd-detected clones above threshold.
1. **Architecture boundary violations** — import-linter and architecture test ratchets.

Each surface has its own ratchet mechanism preventing regression while allowing
tracked exceptions.

Freshness note: rebaseline when debt inventory changes materially.

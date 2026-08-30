______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-28'

______________________________________________________________________

# Project audit prompt surfaces

This directory contains the active project router and a frozen full-text
snapshot. It is navigation only, not runtime SSOT.

## Active sources

- Router: [pack.md](pack.md) (`prompt.audit.project.pack`).
- Ten maintained domain cards: [cycle index](../cycle/README.md).
- Sequential run: [sequential-run.md](../sequential-run.md).
- Cyclic router: [cyclic-pack.md](../cyclic-pack.md).

## Full-text snapshot

[materialized-v3](materialized-v3/README.md) contains the dated 24-card
operator-paste snapshot and its master orchestrator. Those files are frozen
evidence and MUST NOT be edited as source cards.

The retired `full/`, `new/`, and `new2/` trees are not shipping surfaces and
must not be referenced by the prompt registry. Use maintained source cards or
the dated materialized snapshot above.

# LF1-20 Run Explorer status evidence

Scope: offline check of the changed panel in `bioetl-run-explorer-v1`.
The dashboard source checked here is `de6e8f701cc9722a68a64232ef1bb9dfe42fa246`.
Deployment SHA and live panel matrix: `NOT_VERIFIABLE`.

## Panel 3010

- Title: Inspect Recent Runs (last 10).
- Query references: A.
- Generated noValue: UNKNOWN — required launch evidence is unavailable. QUERY ERROR means the backend request failed, not an empty fleet.
- Default value mappings: `[]`.
- Default thresholds: `null`.
- The checked UID does not contain panels 9481 or 9604.

The local generator and owning checks verify the static JSON and its Scenes
ledger. Four historical browser checks skipped because the saved render
artifact was unavailable. No live HTTP response or panel color was observed.
The success, valid empty, missing evidence, not found and request failure
matrix remains pending for live acceptance.

# Advisory Vendor Evidence Contract

## Required invocation properties

- AgentDebugX: `analyze --mode deterministic`; no LLM credentials.
- ProofAgent: `session --tool generic --assess never --no-upload`.
- Fresh subprocess for every run, with a bounded timeout and secret-stripped
  environment.
- Inputs only from the adapter allowlist; outputs only from the adapter-owned
  report subtree.

## Interpretation

AgentDebugX output is diagnostic evidence. ProofAgent output is normalized to
`PASS`, `WARN`, `FAIL`, or `UNAVAILABLE`, always with `advisory: true` and
`lifecycle_authority: false`.

Vendor evidence can suggest investigation or confirm a native finding. It
cannot replace tests, architecture gates, Proof-or-Stop required receipts,
human acceptance criteria, or current-SHA CI.

## Failure handling

Treat missing packages, version drift, timeout, non-standard exit, malformed
JSON, source-binding failure, and redaction failure as unavailable evidence.
Continue with manual inspection and repository-native tooling.


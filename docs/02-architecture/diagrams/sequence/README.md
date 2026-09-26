______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Sequence Diagrams

**Issue:** #6544 · **Policy:** ADR-040

| # | Diagram | File |
| --- | --- | --- |
| 1 | Pipeline execution | [01-pipeline-execution-sequence.mmd](01-pipeline-execution-sequence.mmd) |
| 2 | Composite pipeline | [02-composite-pipeline-sequence.mmd](02-composite-pipeline-sequence.mmd) |
| 3 | HTTP request/response (ADR-032) | [03-http-request-response-flow.mmd](03-http-request-response-flow.mmd) |
| 4 | DQ validation | [04-dq-validation-sequence.mmd](04-dq-validation-sequence.mmd) |
| 5 | Quarantine handling | [05-quarantine-handling-sequence.mmd](05-quarantine-handling-sequence.mmd) |

Lint: `python -m scripts.diagrams lint` (sources). PNG is CI/local-only after DOC-GOV-02.

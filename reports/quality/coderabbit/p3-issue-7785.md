            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/preflight`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/preflight/medallion_validator_idempotency.py`: In @src/bioetl/application/core/preflight/medallion_validator_idempotency.py around lines 57 - 70, Update the append-mode validation branch in the idempotency validator so ConfigValidationError.expected is generated from APPEND_SAFE_IDEMPOTENCY_CONTRACTS instead of hardcoded c...
- **major** `src/bioetl/application/core/preflight/service.py`: In @src/bioetl/application/core/preflight/service.py around lines 54 - 64, Update the preflight call in the surrounding service flow to resolve whether validate_infrastructure supports the raise_on_unhealthy keyword via signature introspection before invoking it, rather than c...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.


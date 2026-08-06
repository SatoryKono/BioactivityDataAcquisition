            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/wiring`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/wiring/__init__.py`: In @src/bioetl/application/core/wiring/__init__.py around lines 20 - 33, Replace the import-time `_build_export_groups()` call with a static or metadata-only export-to-module mapping so package initialization never imports wiring submodules; preserve `_EXPORT_MODULES` and `__a...
- **major** `src/bioetl/application/core/wiring/transformer.py`: In @src/bioetl/application/core/wiring/transformer.py around lines 14 - 26, Add contract tests for every symbol in _PUBLIC_EXPORTS via bioetl.application.core.wiring.transformer, asserting __all__ and direct imports resolve correctly. Verify importing the facade does not eager...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.


            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/lifecycle`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/lifecycle/cleanup_service.py`: In @src/bioetl/application/core/lifecycle/cleanup_service.py around lines 140 - 153, Update the async preview method around CleanupStorageProtocol.preview_cleanup to offload the synchronous filesystem scan to a worker thread, such as via asyncio.to_thread, and await its result...
- **major** `src/bioetl/application/core/lifecycle/heartbeat.py`: In @src/bioetl/application/core/lifecycle/heartbeat.py around lines 82 - 90, Update _heartbeat_loop() so that when lock loss occurs it logs the loss, calls request(), and returns immediately rather than allowing PipelineShutdownError to complete the background task. In stop(),...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.


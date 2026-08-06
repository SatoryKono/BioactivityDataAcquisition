            ## Source

            - Epic: #7688
            - Wave parent: #7691
            - Wave: **B**
            - Path cluster: `src/bioetl/infrastructure/storage/support`
            - Severity counts: `{'major': 3}`

            ## Findings (top)

            - **major** `src/bioetl/infrastructure/storage/support/checkpoint_writer.py`: In @src/bioetl/infrastructure/storage/support/checkpoint_writer.py around lines 28 - 49, Validate every user-supplied path before filesystem access in the checkpoint storage methods, including read, write_atomic, delete, exists, and pattern-based operations. Resolve the config...
- **major** `src/bioetl/infrastructure/storage/support/checkpoint_writer.py`: In @src/bioetl/infrastructure/storage/support/checkpoint_writer.py around lines 35 - 43, Update the atomic write logic in CheckpointWriter.write_atomic to create a unique temporary file within full.parent for every write instead of using full.with_suffix(".tmp"). Write and rep...
- **major** `src/bioetl/infrastructure/storage/support/checkpoint_writer.py`: In @src/bioetl/infrastructure/storage/support/checkpoint_writer.py at line 31, Update the checkpoint read and listing methods around read_text() and the glob/list sorting flow to enforce configured maximum checkpoint bytes and maximum match count before loading file contents o...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.


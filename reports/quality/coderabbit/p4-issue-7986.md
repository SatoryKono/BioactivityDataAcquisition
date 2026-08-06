            ## Source

            - Epic: #7688
            - Wave parent: #7691
            - Wave: **B**
            - Path cluster: `src/bioetl/infrastructure/storage/bronze`
            - Severity counts: `{'major': 4}`

            ## Findings (top)

            - **major** `src/bioetl/infrastructure/storage/bronze/facade_contracts.py`: In @src/bioetl/infrastructure/storage/bronze/facade_contracts.py around lines 17 - 23, Remove the duplicate BRONZE_WRITE_ERRORS definition from io_mixin.py and import the canonical tuple from facade_contracts.py, after confirming this dependency does not create an import cycle...
- **major** `src/bioetl/infrastructure/storage/bronze/io_mixin.py`: In @src/bioetl/infrastructure/storage/bronze/io_mixin.py around lines 54 - 103, Restructure _write_atomic_stream so tempfile.mkstemp resources are protected immediately: ensure the raw fd is closed if ZstdCompressor construction or setup fails, and use a finally block to unlin...
- **major** `src/bioetl/infrastructure/storage/bronze/io_mixin.py`: In @src/bioetl/infrastructure/storage/bronze/io_mixin.py around lines 105 - 121, The _compressed_payload_matches method compares decompressed chunks positionally, so differing read boundaries can falsely report mismatches. Update it to compare the complete decompressed streams...
- **major** `src/bioetl/infrastructure/storage/bronze/metadata_paths.py`: In @src/bioetl/infrastructure/storage/bronze/metadata_paths.py around lines 14 - 19, Add unit tests for calculate_bronze_completed_at covering deterministic start-plus-duration timestamps, and for resolve_bronze_metadata_base_path covering both flat_structure=true and flat_str...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.


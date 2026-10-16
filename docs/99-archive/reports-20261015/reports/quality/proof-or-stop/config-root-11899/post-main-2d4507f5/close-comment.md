Закрываю #11899: fallback gap устранён и полная применимая приёмка завершена.

Acceptance выполнен. [PR #11948](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/11948) MERGED в фактический main `2d4507f595d03591c3db72b2aa554d7f41329ce3`.

- Meaningful fallback/marker/cwd tests исправляют missing line32 и branches25→32,28→25,58→60 из R11; rooted-path regression сохранён. R11 запускал real-checkout сценарии, которые не исполняли synthetic fallback. Production behavior не менялся ради процента покрытия.
- [Полный independent CircleCI producer/acceptance #2356](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2356), реальный delivery SHA `6536a1934d1ce4459a9ed25f4f1eade134dd5ba3`: 17/17 canonical shards, 32878 PASS,175 SKIP,0 failures/errors; line99.70%,branch94.35%. **config_root:40/40 lines,18/18 branches**. Все17 JUnit semantic hashes и raw XML SHA проверены.
- Source SHA256 `4db123e5e95045405ceb710e2425c1cd0e733fb6a225dccc7fc4146c63eaacb5`, test SHA256 `8eda05d84247514c788836919a2df950d4bc92ac06948537a8040b6c9942f9f6`. W48 на actual main c619 сохранён в merged evidence и является ancestor итогового main; local_single_host не переименован в CI.
- Полный architecture suite #2356:4997 PASS,7 SKIP,0 failures/errors. Governance,docs,debt,quality exit0. Исходный bundle `circleci-closeout-2356-6536a1934d1c` получил **ADMIT**; digest `04bbbbc8d518942a0b6003587e24f95b315cfd23c2fc4297ce7928c5e04eed49`. Canonical verifier на чистом exact-SHA checkout независимо подтвердил ADMIT с включённым source check. [Original CI artifacts API](https://circleci.com/api/v2/project/gh/SatoryKono/BioactivityDataAcquisition/2356/artifacts) содержит79 сохранённых artifacts. CI raw SQLite files не опубликованы; их хеши представлены original manifest, не заявляются как повторно вычисленные локально.
- Git trees CI delivery/main равны: `6ad9cf9281fd8bb7bfa8c273784ef6f8b27afdfb`. Post-main owning verification на actual `2d4507f5`: **121 PASS,0 SKIP,exit0**, SHA before/after неизменен. Config-root behavior/governance, inventory completeness/freshness, telemetry, skip census и CircleCI contracts PASS; full-tree guard и ancestry W48 PASS.
- Inventory roster2552 полностью совпадает с canonical measured candidate. Historical floor, thresholds,budgets,exemptions сохранены. Direct raw candidate regression guard остаётся FAIL для других модулей:81 rows ниже retained coverage, ledger опубликован отдельно; measured metrics #2193/#2356 идентичны для всех2552 classes. Global measured nonregression не заявляется, эти residuals не объявлены исправленными задачей config_root.
- Исходный #2193 STOP сохранён; stale VCR catalog исправлен canonical regeneration (один owner). Все26 обычных jobs нового pipeline PASS. Отдельный API repair-agent chunk-task получил max-turns/HTTP429 и не создал commit: это external-agent failure, не test regression. Merge выполнен обычным squash без bypass/admin.

Runtime mirror sync N/A: .codex/.junie не менялись. .env не менялся. Historical R11 context ниже сохранён; текущий closeout не подменяет его measurements.

## Выполненный план и исторический контекст


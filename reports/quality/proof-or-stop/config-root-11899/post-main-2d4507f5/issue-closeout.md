## Closeout — 2026-10-05

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

Первоначальное расхождение зафиксировано полным `f042bfb-r2` producer: `config_root.py` измерен в 90%, исторический baseline был 97.5%. Исходный failed guard и raw candidate сохранены в предыдущем immutable evidence.

Последующий полный canonical **R11** на `f9d20f27b43bc9cdc2b2dbd2d23aafce6fa94854`, source SHA-256 `5115449e8c670f5393a58c7009693f666f0eff818fbaa80e0e9ea63f9827ae0f`, независимо проверен: 17 groups, 32 256 PASS, 181 SKIP, 0 failures/errors; line 99.69%, branch 94.32%. Его raw candidate измеряет `config_root.py` в **97.5%**. Принятый параллельный historical inventory сохраняет **100%** для этого модуля; canonical monotonic adoption не утверждает, что 100% измерены новым R11.

Всего у R11 candidate есть 69 строк ниже исторически принятых per-module значений. Они явно перечислены в ledger. Inventory содержит все 2548 текущих модулей, guards проходят без увеличения budget/threshold; отдельный direct measured candidate regression guard возвращает failure и сохранён.

[Current measured candidate, retained-row ledger и независимый R11 receipt](https://github.com/SatoryKono/BioactivityDataAcquisition/tree/06fdb533aaa69456d1480f902cc149a02a21385f/reports/quality/proof-or-stop/grafana-11874-11844).

Задача остаётся открытой: установить причину разницы test selection/execution/provenance, добавить содержательные проверки недостающих branches при необходимости и подтвердить новое измерение полным canonical producer. Не снижать исторический baseline и не выдавать retained historical rows за новые measurements. CI остаётся BLOCKED_EXTERNAL_PERMANENT.

## Пофайловый план закрытия — 2026-10-03

Проверенный remote main: `1a3cb433b3e02f5cf09d796627a6f07e75c53e8e`. PR #11900 уже MERGED (`1a3cb433b3e02f5cf09d796627a6f07e75c53e8e`); его rooted-path тест не является доказательством закрытия fallback. В independently preserved raw R11 XML config_root:line-rate0.975,branch-rate0.8333; строка32 hits=0, missing branch targets25->32,28->25,58->60. Источник: immutable evidence tree06fdb533aaa69456d1480f902cc149a02a21385f, reports/quality/proof-or-stop/grafana-11874-11844/verified-r11-coverage/coverage.xml. Это новый установленный пробел; прежняя rooted-path causal hypothesis не объясняет missing line32.

### Порядок

1. Зафиксировать source mapping и exact missing lines/branches из raw XML, сравнить historical measurement provenance и test selection.
2. Добавить сценарии fallback/markers/cwd и запустить targeted coverage; подтвердить fallback behavior assertions и40/40 реально выполненных строк. Проценты branch сравнивать отдельно от line.
3. Выполнить новый полный canonical producer на одном pinned source/test tree, все17 групп и завершающий JUnit/exit evidence; targeted100% не заменяет полный producer.
4. Построить raw measured candidate; сравнить config_root и полный retained-row ledger. Сохранить direct candidate guard outcome честно. Если прочие из69 исторических строк остаются ниже, оформить точные residual issues/ledger; не считать их автоматически исправленными этой задачей.
5. Canonical nonregressing adoption и owning guards; publication/merge/проверка итогового main, актуализация issue и закрытие после применимой приёмки.

### Пофайловые действия

- [x] `src/bioetl/infrastructure/config/config_root.py` — Зафиксировать mapping raw R11 XML к source: строка32 return source_path.parents[4] имеет hits=0. Missing branch targets:25->32,28->25,58->60. Production behavior не менять ради покрытия; при доказанном runtime defect открыть отдельную обоснованную правку.
- [x] `tests/unit/infrastructure/config/test_config_root.py` — Добавить тест get_default_repo_root fallback с изолированным synthetic source layout и controlled filesystem: ни один candidate не содержит допустимую пару configs + pyproject.toml/AGENTS.md. Assert точное source_path.parents[4]; fixture не должна случайно находить реальный checkout.
- [x] `tests/unit/infrastructure/config/test_config_root.py` — Добавить meaningful cases: configs есть, но оба markers отсутствуют и поиск продолжается; предпочитаемый cwd_configs отсутствует и выбирается repo/configs. Проверить missing branches из raw XML, не предполагать что rooted-path тест исправляет fallback.
- [x] `tests/unit/infrastructure/config/test_config_root.py` — Сохранить уже merged #11900 rooted-path regression с PureWindowsPath; добавить его к owning selection без повторного внедрения или удаления.
- [x] `tests/architecture/test_config_root_governance.py` — Подтвердить, что canonical config-root governance и отсутствие зависимости от случайного cwd не регрессировали.
- [x] `scripts/engineering/qa/run_local_coverage_verify.py` — Использовать существующий полный 17-group producer на pinned full checkout; не менять selection/exclusions/gates ради зелёного результата. Зафиксировать SHA до/после, Python/platform, test selection, shard exit codes/JUnit/hashes.
- [x] `scripts/engineering/qa/report_module_coverage_inventory.py` — Использовать canonical reporter для raw measured candidate и nonregressing adoption; не выдавать сохранённую historical row за новое измерение.
- [x] `reports/quality/module-coverage-inventory.json` — После нового producer проверить реальные 40/40 строк config_root, source identity и точный inventory path set; historical100% не снижать и не править coverage вручную.
- [x] `tests/architecture/test_module_coverage_inventory.py` — Подтвердить принятую shape и completeness inventory; passing retained-inventory gate не заменяет direct measured candidate comparison.
- [x] `tests/architecture/test_module_coverage_inventory_freshness.py` — Подтвердить актуальный source_tree_sha256, без skip из-за moving/dirty checkout.

### Команды проверки

Windows: `.venv-win/Scripts/python.exe`; использовать full isolated checkout и его src. Raw XML, manifests, shard hashes/JUnit и candidate diff сохранять в новом immutable proof bundle под reports/quality/proof-or-stop/ с собственным run identity. Не перезаписывать R11.

```text
python -m pytest tests/unit/infrastructure/config/test_config_root.py tests/architecture/test_config_root_governance.py --cov=bioetl.infrastructure.config.config_root --cov-branch --cov-report=term-missing --cov-report=xml:reports/quality/config-root-targeted-coverage.xml
python -m scripts.engineering.qa.run_local_coverage_verify
python -m pytest tests/architecture/test_module_coverage_inventory.py tests/architecture/test_module_coverage_inventory_freshness.py
```

### Критерии завершения

- [x] Missing line32 и необходимые ветви покрыты meaningful tests; причина historical/R11 расхождения объяснена.
- [x] Новый полный producer завершился без failures/errors, config_root действительно измерен40/40; branch result и skipped cases перечислены.
- [x] Targeted и full evidence привязаны к SHA/test selection; historical100% не подменяет measurement.
- [x] Retained-row ledger обновлён, оставшиеся module regressions видны отдельно; global nonregression не заявлен при failed direct candidate guard.
- [x] Candidate/inventory paths и source hash guards прошли, thresholds/budgets/exemptions неизменны; применимая приёмка выполнена.

### Ограничения, синхронизация и закрытие

- Billing lock постоянный: `CI=BLOCKED_EXTERNAL_PERMANENT`. Локальные результаты не объявлять CI PASS. Проверить применимый lifecycle/trust policy; при требуемом ADMIT получить реальную допустимую независимую аттестацию, а не переименовать local_single_host в independent evaluator. Снятие billing lock не является шагом этого плана.
- `.env` не менять. Budgets, thresholds, exemptions и exclusions не повышать. Исторические evidence не переписывать.
- #11854 владеет architecture/census/hotspot/scorecard отчётами; #11899 владеет config-root tests, raw coverage producer и обновлением module inventory. Общие quality artifacts регенерировать одним владельцем после интеграции; не запускать конфликтующие publishers параллельно.
- CI-family rebind: `python -m scripts.engineering.qa refresh-ci-drift-families`; не использовать budget-ratcheting refresh для telemetry/test-governance/flaky/evidence/remote-main/dataflow.
- При docs link/header changes: `python -m scripts.docs generate-cleanup-inventory --update`, затем `--check` и `python -m scripts.docs check-links`. Если docs менялись, выполнить требуемый docs verify.
- `git diff --check`; `python scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD`. Runtime mirror parity N/A при неизменных .codex/.junie surfaces; если они менялись, выполнить canonical parity check.
- Перечислить PASS/FAIL/SKIP и ограничения раздельно; опубликовать immutable evidence, пройти применимую приёмку, затем закрыть issue. План выполнен; актуальные результаты приведены в closeout выше.

## Summary
CLI-команды debug и run-manifest завершаются необработанным исключением вместо `ExitCode`.

## Findings
- `interfaces/cli/commands/debug.py:222-226` (major): default `--mode` приводит к непойманному `ValueError`. Нужна валидация до `asyncio.run` и `echo_error` + `ExitCode.CONFIG_ERROR`.
- `interfaces/cli/commands/run_manifest.py:89-96` (major): ветки `RunManifestInspectionCorruptionError` и `ValueError` делают `return` вместо `ExitCode.FAIL` (с `echo_error` и связкой `SystemExit`).

## Acceptance
- [ ] Default debug mode не роняет процесс необработанным `ValueError`.
- [ ] Corruption/ValueError в `run-manifest show` → ненулевой exit code.
- [ ] Тесты на оба пути.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S05-interfaces.jsonl`. Critical `manifest_id` вынесен отдельно.

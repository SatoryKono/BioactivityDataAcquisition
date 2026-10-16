## Summary
HTTP/CLI контрактные мелочи control-plane и health: severity mapping, нули вместо missing metrics, cleanup при `stop()`, `--override` без `=`, мёртвые константы, утечка `data_root`.

## Findings
- `control_plane_identity/types.py:162-172` (major): явный `missing_severity` (включая DEGRADED) не должен переписываться legacy-маппингом `implementation_status`.
- `control_plane_identity/severity.py:74-75` (minor): substring-match якорей; `replay_of_run_id` не должен становиться FAILING из-за `run_id`.
- `processed_records_table.py:135-137` (minor): missing metrics инициализировать `None`, не `0`.
- `health/server_integration_lifecycle.py:211-218` (minor): `close_health_server_resources` должен выполниться, даже если `server.stop()` бросил исключение.
- `config_dq.py:198-202` (minor): `--override` без `=` → `click.BadParameter`.
- `_pipeline_run_report_sections.py:90-114` (trivial): удалить неиспользуемые дубликаты лейблов.
- `_health_server_routing_support.py:186` (minor): readiness не должен отдавать host path в `data_root`.

## Acceptance
- [ ] Явный severity и exact-token status покрыты тестами.
- [ ] Missing metrics ≠ 0.
- [ ] Readiness не содержит filesystem path.
- [ ] `--override` без `=` — понятная ошибка Click.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S05-interfaces.jsonl`.

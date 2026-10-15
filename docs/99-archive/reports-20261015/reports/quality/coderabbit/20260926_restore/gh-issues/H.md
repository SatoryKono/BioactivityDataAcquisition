## Summary
`diagnostics checkpoint` не принимает `manifest_id`, хотя Click-опция его передаёт. Диагностика checkpoint не может сузить осмотр до конкретного manifest.

## Finding (актуально на HEAD)
- `src/bioetl/interfaces/cli/commands/diagnostics.py:237-242` (critical, S05): `diagnostics_checkpoint` принимает только `pipeline`, `run_id`, `audit_limit`, `output_format`. Нужно пробросить optional `manifest_id` в `emit_checkpoint_diagnostics` → `inspect_checkpoint_workflow`. Поведение без `manifest_id` сохранить.

## Acceptance
- [ ] Сигнатура и вызов принимают optional `manifest_id`.
- [ ] CLI help показывает опцию; отсутствие значения не меняет текущий путь.
- [ ] Тест: вызов с `manifest_id` доходит до inspection service.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S05-interfaces.jsonl` (restore 2026-09-26).

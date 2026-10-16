## Summary
Форма записи и внедрение метрик расходятся с контрактом: success/failure validation shape, dedup key из `None`, частичный inject metrics затирается.

## Findings
- `infrastructure/adapters/validation.py:176-186` (major): success возвращает `model_dump`, failure — исходный record; ключи расходятся.
- `infrastructure/adapters/common/deduplication.py:144-145` (major): `None` primary field становится строкой; нужен `None` до конверсии.
- `infrastructure/adapters/_base_runtime.py:63-67` (minor): частичный inject `adapter_metrics` / `request_collector` отбрасывается; default не должен перезаписывать уже заданное.

## Acceptance
- [ ] Оба пути validation сохраняют одну форму record.
- [ ] `build_record_dedup_key(None)` → `None`.
- [ ] Тест на частичный inject: заданный объект не затирается.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S03-infra-adapters.jsonl`.

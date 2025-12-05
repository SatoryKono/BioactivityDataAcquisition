# 04 Testing

## Типы тестов
- Юнит: изолированные проверки без сети (мокаем HTTP/FS), напр. `tests/bioetl/infrastructure/clients/chembl/test_http_client.py`.
- Стадии пайплайна: тесты extract/transform/validate/write с фикстурами (`tests/bioetl/application/pipelines/test_pipeline_base.py`).
- Golden: сравнение артефактов и meta (`tests/golden/*`) — обновлять осознанно.
- Интеграция/смоук: end-to-end через CLI с `--dry-run`/`--limit`.

## Покрытие
- Цель: ≥85% для критичных модулей; не опускать покрытие в CI.
- Проверять детерминизм: стабильная сортировка, хеши, `column_order`.

## Подходы
- Сеть запрещена в unit: использовать моки UnifiedAPIClient/RateLimiter/RetryPolicy.
- Для transform/validate — Pandera-схемы и фиктивные таблицы.
- Проверять `meta.yaml`, checksum, стабильный порядок строк/колонок.

## Детализированные сценарии
- ErrorPolicy: fail-fast vs skip/retry через `ErrorPolicyABC`.
- Dry-run: запись пропускается, validate выполняется, meta отражает dry_run.
- Retry/Rate limit: проверять, что повторные попытки идут с backoff и без превышения лимитов.
- Golden-артефакты: регенерировать только при осознанных изменениях схем/логики; фиксировать в CHANGELOG.

## Практика запуска
- Смоук: `bioetl run --pipeline chembl_activity --config configs/pipelines/chembl/activity.yaml --profile dev --limit 100 --dry-run`.
- Unit-селективно: `pytest tests/bioetl/infrastructure/clients/chembl/test_http_client.py -q`.

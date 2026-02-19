# Contracts Registry

JSON-экспорты в `docs/04-reference/contracts/gold/*.json` — **source of truth** для контрактов Gold-слоя.

Правило синхронизации:

- либо кодовые Pandera-контракты в `src/bioetl/domain/contracts/gold/` генерируются из exported JSON;
- либо любые изменения в кодовых контрактах обязаны проходить parity-check с exported JSON (без расхождений по `name/type/nullable/description`).

Обновление выполняется скриптом:

```bash
python src/tools/scripts/generate-contracts.py
```

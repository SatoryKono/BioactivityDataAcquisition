# Contracts Registry

Кодовые контракты в `src/bioetl/domain/contracts/gold/` — **source of truth** для
контрактов Gold-слоя. JSON-экспорты в `docs/04-reference/contracts/gold/*.json`
являются сгенерированными артефактами для публикации и обзора.

Правило синхронизации:

- изменения в `src/bioetl/domain/contracts/gold/` выполняются в коде;
- после изменения кодовых контрактов необходимо перегенерировать exported JSON;
- parity-check между кодом и exported JSON не должен допускать расхождений по `name/type/nullable/description`.

Обновление выполняется скриптом:

```bash
python scripts/schema/generate_contracts.py
```

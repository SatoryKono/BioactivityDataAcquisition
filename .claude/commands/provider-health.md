---
description: Проверка здоровья провайдеров BioETL — адаптеры, rate limits, VCR cassettes, contract tests. Действия: status, check, contracts, cassettes, rate-limits.
---

# /provider-health

Проверка здоровья провайдеров BioETL: адаптеры, rate limits, контракты, VCR cassettes.

## Использование
```
/provider-health [action] [provider]
```

**Действия:** `status` (default), `check`, `contracts`, `cassettes`, `rate-limits`
**Providers:** `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`

---

## Инструкции

### `status` (default)

For each of 7 providers:

1. **Config:** `configs/providers/{provider}.yaml`
2. **Adapter:** `src/bioetl/infrastructure/adapters/{provider}/client.py` — check `health_check()` (ARCH-004), extract base_url, timeout, max_retries, rate_limit
3. **Entities:** `ls configs/entities/{provider}/`
4. **Cassettes:** `find tests/fixtures/vcr/{provider}/ -name "*.yaml" 2>/dev/null | wc -l`
5. **Contracts:** `find tests/contract/ -name "*{provider}*" -type f 2>/dev/null`

Dashboard:
```
| Provider | Entities | health_check | Rate Limit | Cassettes | Contracts | Status |
|----------|:--------:|:------------:|:----------:|:---------:|:---------:|:------:|
```
Status: 🟢 OK, 🟡 warnings (few cassettes/contracts), 🔴 problems (no health_check)

### `check`
```bash
uv run python -m pytest tests/integration/ -k "{provider}" -k "health" -v --tb=short
# Fallback:
uv run python -m pytest tests/unit/ -k "{provider}" -k "health" -v --tb=short
```

### `contracts`
```bash
uv run python -m pytest tests/contract/ -k "{provider}" -v --tb=short
```

### `cassettes`
```bash
find tests/fixtures/vcr/ -name "*.yaml" -type f | sort
```
Per provider: count, last update (git log), size, orphan cassettes.

### `rate-limits`
Extract from `configs/providers/{provider}.yaml` (rate_limit section) and adapter `client.py` constants.
Table: provider, requests/second, burst, strategy (token_bucket/sliding_window).

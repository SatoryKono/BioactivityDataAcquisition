# /provider-health

Проверка здоровья провайдеров BioETL: адаптеры, rate limits, контракты, VCR cassettes.

## Использование

```
/provider-health [action] [provider]
```

**Действия:**
- `status` — показать статус всех провайдеров (по умолчанию)
- `check` — проверить health_check конкретного провайдера
- `contracts` — проверить API contract stability
- `cassettes` — инвентаризация VCR cassettes
- `rate-limits` — показать конфигурацию rate limiting

**Provider (опционально):**
- `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`
- Без provider — все провайдеры

**Примеры:**
```
/provider-health                            # статус всех провайдеров
/provider-health check chembl               # health check ChEMBL
/provider-health contracts pubmed           # contract тесты PubMed
/provider-health cassettes                  # инвентаризация всех cassettes
/provider-health rate-limits                # rate limit конфигурации
```

---

## Инструкции для Claude

### Действие: `status` (по умолчанию)

Для каждого из 7 провайдеров собрать:

**Шаг 1: Конфигурация**
```bash
# Прочитать provider config
cat configs/providers/{provider}.yaml
```

**Шаг 2: Адаптер**
- Найти `src/bioetl/infrastructure/adapters/{provider}/client.py`
- Проверить: есть ли `health_check()` метод (ARCH-004 requirement)
- Извлечь: base_url, timeout, max_retries, rate_limit settings

**Шаг 3: Entities**
```bash
# Перечислить entity конфиги
ls configs/entities/{provider}/
```

**Шаг 4: VCR Cassettes**
```bash
# Посчитать cassettes
find tests/fixtures/vcr/{provider}/ -name "*.yaml" 2>/dev/null | wc -l
```

**Шаг 5: Contract Tests**
```bash
# Проверить наличие contract тестов
find tests/contract/ -name "*{provider}*" -type f 2>/dev/null
```

**Шаг 6: Сводная таблица**
```
Provider Health Dashboard
=========================
Date: YYYY-MM-DD

| Provider | Entities | health_check | Rate Limit | Cassettes | Contracts | Status |
|----------|:--------:|:------------:|:----------:|:---------:|:---------:|:------:|
| chembl | 14 | ✅ | 10 req/s | 45 | 8 | 🟢 |
| pubchem | 1 | ✅ | 5 req/s | 12 | 3 | 🟢 |
| uniprot | 2 | ✅ | 25 req/s | 8 | 4 | 🟢 |
| pubmed | 1 | ✅ | 3 req/s | 10 | 2 | 🟢 |
| crossref | 1 | ✅ | 50 req/s | 6 | 2 | 🟢 |
| openalex | 1 | ✅ | 10 req/s | 5 | 2 | 🟢 |
| semanticscholar | 1 | ✅ | 1 req/s | 4 | 1 | 🟡 |
```

Status: 🟢 = всё ОК, 🟡 = warnings (мало cassettes/contracts), 🔴 = проблемы (нет health_check)

### Действие: `check`

Запустить integration тесты health_check для провайдера:
```bash
uv run python -m pytest tests/integration/ -k "{provider}" -k "health" -v --tb=short
```

Если нет integration тестов — проверить unit тесты:
```bash
uv run python -m pytest tests/unit/ -k "{provider}" -k "health" -v --tb=short
```

### Действие: `contracts`

```bash
uv run python -m pytest tests/contract/ -k "{provider}" -v --tb=short
```

Показать: какие endpoints покрыты контрактными тестами, какие нет.

### Действие: `cassettes`

Инвентаризация VCR cassettes:
```bash
find tests/fixtures/vcr/ -name "*.yaml" -type f | sort
```

Для каждого provider:
- Количество cassettes
- Дата последнего обновления (git log)
- Размер файлов
- Есть ли cassettes без соответствующего теста (orphan)

### Действие: `rate-limits`

Извлечь rate limit конфигурацию из:
1. `configs/providers/{provider}.yaml` — секция rate_limit
2. `src/bioetl/infrastructure/adapters/{provider}/client.py` — константы
3. Показать таблицу: provider, requests/second, burst, strategy (token_bucket/sliding_window)

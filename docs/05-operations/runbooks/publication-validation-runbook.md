# Operational Runbook: Publication Validation

**Версия:** 1.0.0
**Дата:** 2026-02-06
**Для:** DevOps, Data Engineers, Support
**Связанный ADR:** ADR-033

---

## Содержание

1. [Обзор](#обзор)
2. [Мониторинг и алерты](#мониторинг-и-алерты)
3. [Диагностика по уровням валидации](#диагностика-по-уровням-валидации)
4. [Общие проблемы и решения](#общие-проблемы-и-решения)
5. [Escalation Path](#escalation-path)
6. [Контакты и ресурсы](#контакты-и-ресурсы)

---

## Обзор

Данный runbook описывает процедуры диагностики и устранения сбоев в **5-уровневой валидационной системе** для публикационных данных BioETL.

**Validation Levels:**
1. Base Validation (Pandera)
2. Structural Validation
3. External Verification
4. Logical Validation
5. Semantic Validation

**Key Metrics:**
- **DQ Pass Rate** — процент записей без ошибок/предупреждений
- **WARN Rate** — процент записей с `-dq-warn=True`
- **FAIL Rate** — процент отклонённых записей
- **Validation Latency** — время выполнения валидации (per level)

---

## Мониторинг и алерты

### Критичные алерты (P1 — немедленная реакция)

#### Alert: HighFailRate

**Триггер:**
```promql
(bioetl-validation-failed-total / bioetl-validation-total) > 0.10
```

**Описание:** Более 10% записей отклонены валидацией

**Действия:**
1. Проверить логи последних запусков:
   ```bash
   # Посмотреть ошибки за последний час
   journalctl -u bioetl-pipeline --since "1 hour ago" | grep "validation-failed"

   # Или из structlog JSON
   cat /var/log/bioetl/pipeline.log | \
     jq 'select(.event == "validation-failed") | select(.timestamp > now - 3600)'
   ```

2. Определить провайдера и уровень с наибольшим fail rate:
   ```bash
   # Топ провайдеров по fail rate
   cat /var/log/bioetl/pipeline.log | \
     jq -r 'select(.event == "validation-failed") | "\(.provider) \(.validation-level)"' | \
     sort | uniq -c | sort -rn | head -10
   ```

3. Если проблема в **Base Validation** → проверить схему (см. [Base Validation Failures](#level-1-base-validation-failures))
4. Если проблема в **External Verification** → проверить доступность API (см. [External Verification Failures](#level-3-external-verification-failures))

---

#### Alert: ValidationLatencyHigh

**Триггер:**
```promql
histogram-quantile(0.95, bioetl-validation-duration-seconds) > 300
```

**Описание:** P95 validation latency > 5 минут

**Действия:**
1. Проверить, какой уровень валидации медленный:
   ```bash
   # Latency по уровням
   cat /var/log/bioetl/pipeline.log | \
     jq 'select(.event == "validation-step-complete") |
         {level: .validator, duration: .duration-seconds}' | \
     jq -s 'group-by(.level) |
            map({level: .[0].level, avg-duration: (map(.duration) | add / length)})'
   ```

2. Если медленный **External Verification**:
   - Проверить rate limiting:
     ```bash
     # Количество 429 ответов от API
     grep "rate-limit-exceeded" /var/log/bioetl/pipeline.log | wc -l
     ```
   - Снизить `batch-size` или увеличить `retry-delay`

3. Если медленный **Semantic Validation**:
   - Отключить временно:
     ```bash
     bioetl run \
       --pipeline pubmed_publication \
       --skip-semantic
     ```

---

### Предупреждающие алерты (P2 — реакция в течение 4 часов)

#### Alert: HighWarnRate

**Триггер:**
```promql
(bioetl-validation-warned-total / bioetl-validation-total) > 0.20
```

**Описание:** Более 20% записей в карантине (`-dq-warn=True`)

**Действия:**
1. Проверить топ правил, вызывающих WARN:
   ```bash
   cat /var/log/bioetl/pipeline.log | \
     jq -r 'select(.event == "validation-warning") | .rule' | \
     sort | uniq -c | sort -rn | head -10
   ```

2. Если топ правило — `doi-not-found`:
   - CrossRef API может быть временно недоступен
   - Проверить вручную:
     ```bash
     curl -I https://api.crossref.org/works/10.1038/nature12373
     ```

3. Если топ правило — `low-title-abstract-similarity`:
   - Semantic validation слишком строгая
   - Увеличить threshold в конфиге

4. **Не требует немедленного action** — записи в карантине доступны для анализа

---

## Диагностика по уровням валидации

### Level 1: Base Validation Failures

**Симптом:** Pandera `SchemaError`, записи отклонены на первом уровне

#### Диагностика

```bash
# 1. Посмотреть последние SchemaError
cat /var/log/bioetl/pipeline.log | \
  jq 'select(.event == "base-validation-failed") | .error' | tail -20

# 2. Проверить, какие колонки fail чаще всего
cat /var/log/bioetl/pipeline.log | \
  jq -r 'select(.event == "base-validation-failed") |
         .error | match("Column \'([^\']+)\'") | .captures[0].string' | \
  sort | uniq -c | sort -rn

# 3. Посмотреть примеры некорректных значений
cat /var/log/bioetl/pipeline.log | \
  jq 'select(.event == "base-validation-failed") |
      {column: .column, value: .invalid-value, record-id: .record-id}' | \
  head -10
```

#### Типичные проблемы

**Проблема 1: Regex mismatch**

```bash
# Пример: DOI не проходит валидацию
# Regex: ^10\.\d{4,9}/.+$
# Некорректное значение: "doi:10.1234/test" (префикс "doi:")

# Проверить реальные DOI в Bronze
python -c "
import pandas as pd
df = pd.read-parquet('data/bronze/crossref/publication.parquet')
print('Sample DOIs:')
print(df['doi'].dropna().head(10))
print('\nDOIs not matching regex:')
print(df[~df['doi'].str.match(r'^10\.\d{4,9}/.+$', na=False)]['doi'].head(10))
"
```

**Решение:**
- Обновить трансформер для удаления префикса `doi:`:
  ```python
  # src/bioetl/application/transformers/crossref-transformer.py
  def transform-doi(raw-doi: str) -> str:
      doi = raw-doi.strip().lower()
      if doi.startswith("doi:"):
          doi = doi[4:]  # Remove "doi:" prefix
      return doi
  ```

---

**Проблема 2: NULL в non-nullable полях**

```bash
# Проверить NULL в Primary Key
python -c "
import pandas as pd
df = pd.read-parquet('data/bronze/pubmed/publication.parquet')
null-pk = df[df['pmid'].isna()]
print(f'Records with NULL pmid: {len(null-pk)}')
if len(null-pk) > 0:
    print('Sample records:')
    print(null-pk[['pmid', 'doi', 'title']].head())
"
```

**Решение:**
- Фильтровать NULL PK в адаптере перед записью в Bronze:
  ```python
  # src/bioetl/infrastructure/adapters/pubmed/client.py
  def fetch-publications(self, query: Query) -> Iterator[RawRecord]:
      for record in self.-fetch-raw(query):
          if record.get("pmid") is None:
              self.-logger.warning("record-missing-pk", record=record)
              continue  # Skip record
          yield record
  ```

---

**Проблема 3: Неправильный тип данных**

```bash
# Проверить типы данных
python -c "
import pandas as pd
df = pd.read-parquet('data/bronze/chembl/publication.parquet')
print('Data types:')
print(df.dtypes)
print('\nPublicationYear non-integer values:')
print(df[~df['publication-year'].apply(lambda x: isinstance(x, (int, float, type(None))))]['publication-year'])
"
```

**Решение:**
- Добавить coercion в трансформере:
  ```python
  def transform-publication-year(raw-year: Any) -> int | None:
      if raw-year is None:
          return None
      try:
          return int(raw-year)
      except (ValueError, TypeError):
          self.-logger.warning("invalid-year", raw-year=raw-year)
          return None
  ```

---

### Level 2: Structural Validation Warnings

**Симптом:** `-dq-warn=True` из-за нарушения межполевых правил

#### Диагностика

```bash
# 1. Топ структурных правил с WARN
cat /var/log/bioetl/pipeline.log | \
  jq -r 'select(.event == "structural-validation-warning") | .rule' | \
  sort | uniq -c | sort -rn

# 2. Примеры записей с нарушением page-ordering
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/pubmed/publication.parquet')
invalid-pages = df[
    df['page-first'].notna() &
    df['page-last'].notna() &
    (df['page-first'].astype(str).str.isnumeric()) &
    (df['page-last'].astype(str).str.isnumeric()) &
    (df['page-first'].astype(int) > df['page-last'].astype(int))
]
print(f'Records with page-first > page-last: {len(invalid-pages)}')
print(invalid-pages[['pmid', 'page-first', 'page-last', '-dq-warn']].head(10))
"
```

#### Типичные проблемы

**Проблема: Year mismatch между `publication-year` и `publication-date`**

```bash
# Найти несоответствия
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/crossref/publication.parquet')
df['publication-date-year'] = pd.to-datetime(df['publication-date'], errors='coerce').dt.year
mismatches = df[
    df['publication-year'].notna() &
    df['publication-date'].notna() &
    (df['publication-year'] != df['publication-date-year'])
]
print(f'Year mismatches: {len(mismatches)}')
print(mismatches[['doi', 'publication-year', 'publication-date']].head(10))
"
```

**Решение:**
- Использовать `publication-date` как source of truth:
  ```python
  def transform(self, raw: RawRecord) -> TransformedRecord:
      pub-date = raw.get("publication-date")
      pub-year = raw.get("publication-year")

      # If date exists, extract year from it
      if pub-date:
          pub-year = datetime.strptime(pub-date, "%Y-%m-%d").year

      return TransformedRecord(
          publication-date=pub-date,
          publication-year=pub-year,
      )
  ```

---

### Level 3: External Verification Failures

**Симптом:** HTTP 404/timeout от upstream API, `-dq-warn=True`

#### Диагностика

```bash
# 1. Проверить доступность API endpoints
curl -I -w "\n%{http-code}\n" https://api.crossref.org/works/10.1038/nature12373
curl -I -w "\n%{http-code}\n" https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=12345678
curl -I -w "\n%{http-code}\n" https://api.openalex.org/works/W2124179640
curl -I -w "\n%{http-code}\n" https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b

# 2. Проверить rate limiting
cat /var/log/bioetl/pipeline.log | \
  jq 'select(.event == "external-api-rate-limited") |
      {provider: .provider, timestamp: .timestamp}' | \
  tail -20

# 3. Количество 404 по провайдерам
cat /var/log/bioetl/pipeline.log | \
  jq -r 'select(.event == "external-id-not-found") | .provider' | \
  sort | uniq -c
```

#### Типичные проблемы

**Проблема 1: CrossRef API rate limit (HTTP 429)**

```bash
# Проверить rate limit конфигурацию
cat config/crossref-validation.yaml | grep -A5 "external-verification"

# Текущая конфигурация:
# rate-limit: 50  # requests per second
```

**Решение:**
- Снизить rate limit:
  ```yaml
  # config/crossref-validation.yaml
  external-verification:
    providers:
      crossref:
        rate-limit: 20  # Reduce from 50 to 20
        batch-size: 50
  ```

- Или добавить exponential backoff:
  ```python
  async def verify-with-retry(self, doi: str) -> VerificationResult:
      for attempt in range(self.-max-retries):
          try:
              response = await self.-client.get(f"/works/{doi}")
              return VerificationResult(status="PASS", found=True)
          except httpx.HTTPStatusError as e:
              if e.response.status-code == 429:
                  delay = 2 ** attempt  # Exponential backoff
                  await asyncio.sleep(delay)
              else:
                  raise
      return VerificationResult(status="WARN", found=False)
  ```

---

**Проблема 2: PubMed NCBI API timeout**

```bash
# Проверить timeout конфигурацию
cat config/pubmed-validation.yaml | grep -A2 "timeout"

# Текущая конфигурация:
# timeout: 10.0  # seconds
```

**Решение:**
- Увеличить timeout для PubMed (NCBI часто медленный):
  ```yaml
  external-verification:
    providers:
      pubmed:
        timeout: 30.0  # Increase from 10 to 30
        rate-limit: 2  # Lower than default 3 to reduce load
  ```

---

**Проблема 3: API недоступен (network issue)**

```bash
# Проверить сетевую связность
ping -c 5 api.crossref.org
traceroute api.crossref.org

# Проверить DNS resolution
nslookup api.crossref.org

# Тест HTTP connectivity
curl -v --connect-timeout 5 https://api.crossref.org/
```

**Решение:**
- Временно отключить External Verification:
  ```bash
  bioetl run \
    --pipeline crossref_publication \
    --skip-external
  ```

- Или отключить только проблемный провайдер:
  ```yaml
  # config/crossref-validation.yaml
  external-verification:
    enabled: true
    providers:
      crossref:
        enabled: false  # Disable temporarily
  ```

---

### Level 4: Logical Validation Warnings

**Симптом:** `-dq-warn=True` из-за нарушения бизнес-правил

#### Диагностика

```bash
# 1. Топ логических правил с WARN
cat /var/log/bioetl/pipeline.log | \
  jq -r 'select(.event == "logical-validation-warning") | .rule' | \
  sort | uniq -c | sort -rn

# 2. Примеры записей с year-out-of-range
python -c "
import pandas as pd
from datetime import date
df = pd.read-parquet('data/silver/pubmed/publication.parquet')
current-year = date.today().year
invalid-years = df[
    df['publication-year'].notna() &
    ((df['publication-year'] < 1800) | (df['publication-year'] > current-year + 1))
]
print(f'Records with invalid publication-year: {len(invalid-years)}')
print(invalid-years[['pmid', 'publication-year', '-dq-warn']].head(10))
"
```

#### Типичные проблемы

**Проблема: Publication year в будущем (> CURRENT-YEAR + 1)**

```bash
# Найти записи с future year
python -c "
import pandas as pd
from datetime import date
df = pd.read-parquet('data/silver/openalex/publication.parquet')
current-year = date.today().year
future-years = df[df['publication-year'] > current-year + 1]
print(f'Records with future year: {len(future-years)}')
print(future-years[['openalex-id', 'publication-year', 'title']].head())
"
```

**Решение:**
- **Не исправлять автоматически** (может быть preprint с корректной датой)
- Пометить как WARN, оставить для ручного review
- Если точно ошибка — обновить в Bronze:
  ```sql
  -- Исправить известные ошибки (например, 2099 → 2019)
  UPDATE bronze.openalex_publication
  SET publication-year = 2019
  WHERE publication-year = 2099;
  ```

---

**Проблема: Negative citations**

```bash
# Найти записи с отрицательными citations
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/semanticscholar/publication.parquet')
negative-cit = df[
    df['citations-received'].notna() &
    (df['citations-received'] < 0)
]
print(f'Records with negative citations: {len(negative-cit)}')
print(negative-cit[['paper-id', 'citations-received', 'title']].head())
"
```

**Решение:**
- **Data quality issue у источника**
- Обнулить некорректные значения в трансформере:
  ```python
  def transform-citations-received(raw-citations: int | None) -> int | None:
      if raw-citations is None:
          return None
      if raw-citations < 0:
          self.-logger.warning("negative-citations", value=raw-citations)
          return 0  # Coerce to 0
      return raw-citations
  ```

---

### Level 5: Semantic Validation Warnings

**Симптом:** `-dq-warn=True` из-за низкой semantic similarity или language mismatch

#### Диагностика

```bash
# 1. Топ semantic правил с WARN
cat /var/log/bioetl/pipeline.log | \
  jq -r 'select(.event == "semantic-validation-warning") | .rule' | \
  sort | uniq -c | sort -rn

# 2. Примеры записей с low-title-abstract-similarity
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/pubmed/publication.parquet')
low-sim = df[
    df['-dq-warn'] == True &
    df['-dq-warn-reasons'].str.contains('low-title-abstract-similarity', na=False)
]
print(f'Records with low title-abstract similarity: {len(low-sim)}')
print(low-sim[['pmid', 'title', 'abstract']].head(3))
"
```

#### Типичные проблемы

**Проблема: False positive — title и abstract семантически связаны, но низкий score**

```bash
# Проверить threshold
cat config/pubmed-validation.yaml | grep -A3 "semantic-validation"

# Текущая конфигурация:
# similarity-threshold: 0.3
```

**Решение:**
- Semantic validation **НЕ блокирует** записи (только WARN)
- Если слишком много false positives — увеличить threshold:
  ```yaml
  semantic-validation:
    enabled: true
    similarity-threshold: 0.2  # Lower threshold (less strict)
  ```

- Или отключить для конкретного провайдера:
  ```yaml
  # config/chembl-validation.yaml
  semantic-validation:
    enabled: false  # Disable for ChEMBL (low quality abstracts)
  ```

---

**Проблема: Language mismatch (detected != declared)**

```bash
# Примеры language mismatch
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/pubmed/publication.parquet')
lang-mismatch = df[
    df['-dq-warn'] == True &
    df['-dq-warn-reasons'].str.contains('language-mismatch', na=False)
]
print(f'Records with language mismatch: {len(lang-mismatch)}')
print(lang-mismatch[['pmid', 'language', 'title', 'abstract']].head())
"
```

**Решение:**
- **Не исправлять автоматически**
- Language detection может быть некорректной для коротких текстов
- Оставить как WARN, не блокировать запись

---

## Общие проблемы и решения

### 1. Pipeline застревает на валидации

**Симптомы:**
- Pipeline выполняется > 2 часов
- CPU usage low, network idle

**Диагностика:**
```bash
# Проверить, какой процесс активен
ps aux | grep bioetl

# Проверить последний лог-event
tail -1 /var/log/bioetl/pipeline.log | jq

# Если застряло на External Verification — проверить active HTTP connections
lsof -i -P -n | grep bioetl
```

**Решение:**
```bash
# Kill pipeline
pkill -f "bioetl.interfaces.cli.main run-pipeline"

# Перезапустить без External Verification
bioetl run \
  --pipeline pubmed_publication \
  --skip-external \
  --skip-semantic
```

---

### 2. Карантинная таблица переполнена

**Симптомы:**
- > 50% записей в карантине (`-dq-warn=True`)
- Silver storage растёт быстрее обычного

**Диагностика:**
```bash
# Количество записей в карантине
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/crossref/publication.parquet')
total = len(df)
quarantine = len(df[df['-dq-warn'] == True])
print(f'Total: {total}, Quarantine: {quarantine}, Percentage: {100 * quarantine / total:.2f}%')
"

# Топ причин попадания в карантин
python -c "
import pandas as pd
df = pd.read-parquet('data/silver/crossref/publication.parquet')
quarantine = df[df['-dq-warn'] == True]
# Assuming -dq-warn-reasons is a JSON string
import json
reasons = quarantine['-dq-warn-reasons'].apply(json.loads).explode()
print(reasons.value-counts().head(10))
"
```

**Решение:**
1. **Если причина — External 404:**
   - Отключить External Verification для следующих запусков
   - Провести manual review топ-N записей

2. **Если причина — Semantic low similarity:**
   - Увеличить threshold или отключить Semantic Validation

3. **Промоция валидных записей из карантина:**
   ```python
   # Автоматически промотировать записи с только одной WARN причиной
   df = pd.read-parquet("data/silver/pubmed/publication.parquet")
   single-warn = df[
       (df["-dq-warn"] == True) &
       (df["-dq-warn-reasons"].str.count(",") == 0)  # Single reason
   ]
   single-warn["-dq-warn"] = False
   single-warn.to-parquet("data/silver/pubmed/publication.parquet", mode="append")
   ```

---

### 3. DQ Metrics отсутствуют в Prometheus

**Симптомы:**
- Grafana dashboard пустой
- Prometheus `/metrics` endpoint не показывает `bioetl-validation-*` метрики

**Диагностика:**
```bash
# Проверить Prometheus endpoint
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job == "bioetl")'

# Проверить метрики напрямую
curl http://localhost:8000/metrics | grep bioetl-validation
```

**Решение:**
```bash
# Перезапустить pipeline с Prometheus exporter
bioetl run \
  --pipeline pubmed_publication \
  --enable-metrics \
  --metrics-port 8000

# Добавить в prometheus.yml:
scrape-configs:
  - job-name: 'bioetl'
    static-configs:
      - targets: ['localhost:8000']
```

---

## Escalation Path

### Level 1: Self-Service (0-30 min)

- Проверить runbook (этот документ)
- Поискать в логах похожие ошибки
- Попробовать стандартные решения (skip validation level, restart)

### Level 2: Team Slack (30 min - 2 hours)

- **Канал:** `#bioetl-support`
- **Упомянуть:** `@data-engineers`
- **Приложить:**
  - Последние 50 строк лога
  - Команду запуска pipeline
  - Скриншот Grafana dashboard (если доступен)

### Level 3: On-Call Engineer (2-4 hours)

- **PagerDuty:** Trigger incident для `bioetl-oncall` rotation
- **Условия эскалации:**
  - FAIL rate > 50%
  - Pipeline полностью застрял > 4 часа
  - Production data loss возможен

### Level 4: Data Engineering Lead (4+ hours)

- **Email:** data-eng-lead@company.com
- **Условия эскалации:**
  - Upstream provider API сломан (требуется связаться с vendor)
  - Архитектурные изменения необходимы
  - SLA нарушено

---

## Контакты и ресурсы

### Внутренние ресурсы

- **Slack канал:** `#bioetl-support`
- **Wiki:** `https://wiki.company.com/bioetl/validation`
- **Runbook repo:** `https://github.com/company/bioetl/tree/main/docs/runbooks`
- **Grafana dashboard:** `https://grafana.company.com/d/bioetl-validation`

### Upstream провайдеры

| Провайдер | Support Email | API Status Page | Rate Limits |
|-----------|---------------|-----------------|-------------|
| CrossRef | support@crossref.org | https://status.crossref.org/ | 50 req/s (polite pool: mailto in User-Agent) |
| PubMed/NCBI | info@ncbi.nlm.nih.gov | https://www.ncbi.nlm.nih.gov/home/about/policies/ | 3 req/s without API key, 10 with key |
| OpenAlex | team@openalex.org | https://status.openalex.org/ | 100,000 req/day (polite pool: mailto in User-Agent) |
| Semantic Scholar | semanticscholar-api@allenai.org | https://www.semanticscholar.org/product/api | 100 req/5min for public API |
| ChEMBL | chembl-help@ebi.ac.uk | https://www.ebi.ac.uk/chembl/ | No official limit (be polite) |

### ADR и документация

- **ADR-033:** Стратегия валидации (`docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md`)
- **Validation Guide:** `docs/03-guides/publication-validation-guide.md`
- **Field Reference:** `docs/04-reference/publication-fields-reference.md`
- **Test Suite:** `tests-generated/` (471 тест)

---

**Версия runbook:** 1.0.0
**Последнее обновление:** 2026-02-06
**Владелец:** Data Engineering Team
**Статус:** Production Ready ✅

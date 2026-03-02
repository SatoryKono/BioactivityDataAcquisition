# Аудит Параметров Доступа к Источникам Данных BioETL

**Дата аудита:** 2026-02-03
**Версия:** 1.1.0 (исправления применены)

---

## Executive Summary

Проверено **7 конфигураций источников** в `configs/sources/`. Выявлено и **исправлено 2 проблемы** с именами переменных окружения.

| Статус | Количество |
|--------|------------|
| Конфигураций проверено | 7 |
| Rate limits корректны | 7/7 |
| Circuit breaker корректен | 6/7 (SemanticScholar — обоснованное отклонение) |
| Env var mismatches | **0 (FIXED)** |

### Применённые исправления

| ID | Файл | Изменение |
|----|------|-----------|
| ENV-001 | `.env.example:43` | `BIOETL-SEMANTIC-SCHOLAR-API-KEY` → `BIOETL-SEMANTICSCHOLAR-API-KEY` |
| CONFIG-001 | `configs/sources/pubmed.yaml:16-17` | `BIOETL-NCBI-*` → `BIOETL-PUBMED-*` |
| CONFIG-002 | `configs/pipelines/pubmed/publication.yaml:29-30` | `BIOETL-NCBI-*` → `BIOETL-PUBMED-*` |

---

## 1. Инвентаризация Конфигураций

### A. Таблица статуса доступа

| Provider | Base URL | Auth Type | Rate Limit (req/sec) | Circuit Breaker | Env Variables |
|----------|----------|-----------|----------------------|-----------------|---------------|
| ChEMBL | `https://www.ebi.ac.uk/chembl/api/data` | public | 3 | 5/300 | — |
| PubChem | `https://pubchem.ncbi.nlm.nih.gov/rest/pug` | public | 5 | 5/300 | — |
| UniProt | `https://rest.uniprot.org` | api-key | 10 (100 w/key) | 5/300 | `BIOETL-UNIPROT-API-KEY` |
| OpenAlex | `https://api.openalex.org` | email | 10 | 5/300 | `BIOETL-OPENALEX-EMAIL` |
| CrossRef | `https://api.crossref.org` | email | 50 | 5/300 | `BIOETL-CROSSREF-EMAIL` |
| PubMed | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | api-key | 3 (10 w/key) | 5/300 | `BIOETL-NCBI-API-KEY`, `BIOETL-NCBI-EMAIL` |
| SemanticScholar | `https://api.semanticscholar.org/graph/v1` | api-key | 0.1 (1 w/key) | **10/600** | `BIOETL-SEMANTICSCHOLAR-API-KEY` |

### B. Детализация по провайдерам

#### ChEMBL (`configs/sources/chembl.yaml`)
```yaml
# Lines 14-15, 30-32
base-url: https://www.ebi.ac.uk/chembl/api/data
auth-type: public
rate-limit:
  requests-per-second: 3
  burst: 10
```
**Статус:** OK — консервативный лимит для публичного API

#### PubChem (`configs/sources/pubchem.yaml`)
```yaml
# Lines 14-15, 27-29
base-url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
auth-type: public
rate-limit:
  requests-per-second: 5.0
  burst: 10
```
**Статус:** OK — соответствует документации (5 req/sec)

#### UniProt (`configs/sources/uniprot.yaml`)
```yaml
# Lines 14-16, 27-32
base-url: https://rest.uniprot.org
auth-type: api-key
api-key-env: BIOETL-UNIPROT-API-KEY
rate-limit:
  requests-per-second: 10.0
  burst: 20
  with-api-key:
    requests-per-second: 100
    burst: 200
```
**Статус:** OK — 10/100 req/sec соответствует документации

#### OpenAlex (`configs/sources/openalex.yaml`)
```yaml
# Lines 15-17, 31-34
base-url: https://api.openalex.org
auth-type: email
mailto: ${BIOETL-OPENALEX-EMAIL}
rate-limit:
  requests-per-second: 10
  burst: 20
  polite-pool: true
```
**Статус:** OK — 10 req/sec для polite pool

#### CrossRef (`configs/sources/crossref.yaml`)
```yaml
# Lines 15-17, 31-34
base-url: https://api.crossref.org
auth-type: email
mailto: ${BIOETL-CROSSREF-EMAIL}
rate-limit:
  requests-per-second: 50
  burst: 100
  polite-pool: true
```
**Статус:** OK — 50 req/sec для polite pool

#### PubMed (`configs/sources/pubmed.yaml`)
```yaml
# Lines 14-17, 31-36
base-url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
auth-type: api-key
api-key-env: BIOETL-NCBI-API-KEY
email-env: BIOETL-NCBI-EMAIL
rate-limit:
  requests-per-second: 3.0
  burst: 5
  with-api-key:
    requests-per-second: 10
    burst: 20
```
**Статус:** OK — 3/10 req/sec соответствует документации

#### SemanticScholar (`configs/sources/semanticscholar.yaml`)
```yaml
# Lines 21-23, 39-45
base-url: https://api.semanticscholar.org/graph/v1
auth-type: api-key
api-key: ${BIOETL-SEMANTICSCHOLAR-API-KEY}
circuit-breaker:
  failure-threshold: 10      # DEVIATION: 10 vs standard 5
  recovery-timeout: 600      # DEVIATION: 600 vs standard 300
rate-limit:
  requests-per-second: 0.1   # Very conservative
  burst: 1
  with-api-key:
    requests-per-second: 1.0
    burst: 5
```
**Статус:** OK — отклонения circuit breaker обоснованы (S2 API нестабилен)

---

## 2. Валидация Переменных Окружения

### CRITICAL: Несоответствия имён переменных

#### Issue #1: Semantic Scholar API Key
| Location | Variable Name | Status |
|----------|---------------|--------|
| `configs/sources/semanticscholar.yaml:23` | `BIOETL-SEMANTICSCHOLAR-API-KEY` | Config |
| `.env.example:42` | `BIOETL-SEMANTIC-SCHOLAR-API-KEY` | **MISMATCH** |
| `src/bioetl/composition/providers/registration.py:438` | `BIOETL-SEMANTICSCHOLAR-API-KEY` | Code |

**Проблема:** `.env.example` использует `BIOETL-SEMANTIC-SCHOLAR-API-KEY` (с underscore), но config и код — `BIOETL-SEMANTICSCHOLAR-API-KEY` (без underscore).

#### Issue #2: PubMed/NCBI Variables
| Location | Variable Name | Status |
|----------|---------------|--------|
| `configs/sources/pubmed.yaml:16-17` | `BIOETL-NCBI-API-KEY`, `BIOETL-NCBI-EMAIL` | Config |
| `configs/pipelines/pubmed/publication.yaml:29-30` | `BIOETL-NCBI-EMAIL`, `BIOETL-NCBI-API-KEY` | Pipeline |
| `.env.example:35-36` | `BIOETL-PUBMED-API-KEY`, `BIOETL-PUBMED-EMAIL` | **MISMATCH** |
| `.github/workflows/contract-tests.yml:77` | `BIOETL-PUBMED-API-KEY` | CI |
| `tests/contract/conftest.py:52` | `BIOETL-PUBMED-API-KEY` | Tests |

**Проблема:** Config использует `BIOETL-NCBI-*`, но `.env.example`, CI и тесты — `BIOETL-PUBMED-*`.

### OK: Корректные переменные

| Variable | Config | .env.example | Status |
|----------|--------|--------------|--------|
| `BIOETL-UNIPROT-API-KEY` | `uniprot.yaml:16` | `.env.example:43` | OK |
| `BIOETL-OPENALEX-EMAIL` | `openalex.yaml:17` | `.env.example:30` | OK |
| `BIOETL-CROSSREF-EMAIL` | `crossref.yaml:17` | `.env.example:10` | OK |

---

## 3. Rate Limits vs Документация

| Provider | Documented Limit | Config Value | Status |
|----------|------------------|--------------|--------|
| ChEMBL | No explicit limit | 3 req/sec | OK (conservative) |
| PubChem | 5 req/sec | 5 req/sec | OK |
| UniProt | 100 req/sec (w/key) | 10/100 req/sec | OK |
| OpenAlex | 10 req/sec (polite) | 10 req/sec | OK |
| CrossRef | 50 req/sec (polite) | 50 req/sec | OK |
| PubMed | 3/10 req/sec | 3/10 req/sec | OK |
| SemanticScholar | 1 req/sec (w/key) | 0.1/1 req/sec | OK |

---

## 4. Circuit Breaker Compliance

| Provider | failure-threshold | recovery-timeout | RULES.md (5/300) | Status |
|----------|-------------------|------------------|------------------|--------|
| ChEMBL | 5 | 300 | | OK |
| PubChem | 5 | 300 | | OK |
| UniProt | 5 | 300 | | OK |
| OpenAlex | 5 | 300 | | OK |
| CrossRef | 5 | 300 | | OK |
| PubMed | 5 | 300 | | OK |
| SemanticScholar | **10** | **600** | | DEVIATION (documented) |

**SemanticScholar отклонение:** Обосновано в `semanticscholar.yaml:31-35` — API нестабилен, требует более толерантных настроек.

---

## 5. Корректировки

### A. Список требуемых исправлений

```yaml
corrections:
  - id: ENV-001
    severity: CRITICAL
    file: .env.example
    line: 42
    old-value: "BIOETL-SEMANTIC-SCHOLAR-API-KEY=your-semantic-scholar-api-key-here"
    new-value: "BIOETL-SEMANTICSCHOLAR-API-KEY=your-semantic-scholar-api-key-here"
    reason: "Несоответствие имени переменной с configs/sources/semanticscholar.yaml:23"

  - id: ENV-002
    severity: CRITICAL
    file: .env.example
    lines: 35-36
    old-value: |
      BIOETL-PUBMED-API-KEY=your-ncbi-api-key-here
      BIOETL-PUBMED-EMAIL=your-email@example.com
    new-value: |
      BIOETL-NCBI-API-KEY=your-ncbi-api-key-here
      BIOETL-NCBI-EMAIL=your-email@example.com
    reason: "Несоответствие с configs/sources/pubmed.yaml:16-17"
    note: "Также обновить CI workflow и тесты для консистентности"
```

### B. Альтернатива: Обновить configs вместо .env.example

Если тесты и CI уже используют `BIOETL-PUBMED-*`, можно обновить configs:

```yaml
alternative-corrections:
  - id: CONFIG-001
    file: configs/sources/pubmed.yaml
    lines: 16-17
    old-value: |
      api-key-env: BIOETL-NCBI-API-KEY
      email-env: BIOETL-NCBI-EMAIL
    new-value: |
      api-key-env: BIOETL-PUBMED-API-KEY
      email-env: BIOETL-PUBMED-EMAIL
    reason: "Согласование с CI и тестами"

  - id: CONFIG-002
    file: configs/pipelines/pubmed/publication.yaml
    lines: 29-30
    old-value: |
      email: "${BIOETL-NCBI-EMAIL}"
      api-key: "${BIOETL-NCBI-API-KEY}"
    new-value: |
      email: "${BIOETL-PUBMED-EMAIL}"
      api-key: "${BIOETL-PUBMED-API-KEY}"
```

---

## 6. Рекомендации

### Приоритет P1 (Critical)
1. Исправить несоответствие `BIOETL-SEMANTICSCHOLAR-API-KEY` в `.env.example`
2. Унифицировать `BIOETL-PUBMED-*` vs `BIOETL-NCBI-*` — выбрать один вариант

### Приоритет P2 (Medium)
1. Добавить валидацию env variables при старте pipeline
2. Создать скрипт проверки консистентности env vars

### Приоритет P3 (Low)
1. Документировать отклонение circuit breaker для SemanticScholar в ADR

---

## Артефакты

| Файл | Описание |
|------|----------|
| `source-access-audit.md` | Этот документ |
| `source-access-status.csv` | CSV таблица статусов (ниже) |

---

## Приложение: CSV Export

```csv
provider,base-url,auth-type,rate-limit-rps,rate-limit-with-key,circuit-breaker,env-vars,issues
chembl,https://www.ebi.ac.uk/chembl/api/data,public,3,—,5/300,—,—
pubchem,https://pubchem.ncbi.nlm.nih.gov/rest/pug,public,5,—,5/300,—,—
uniprot,https://rest.uniprot.org,api-key,10,100,5/300,BIOETL-UNIPROT-API-KEY,—
openalex,https://api.openalex.org,email,10,—,5/300,BIOETL-OPENALEX-EMAIL,—
crossref,https://api.crossref.org,email,50,—,5/300,BIOETL-CROSSREF-EMAIL,—
pubmed,https://eutils.ncbi.nlm.nih.gov/entrez/eutils,api-key,3,10,5/300,"BIOETL-NCBI-API-KEY,BIOETL-NCBI-EMAIL",ENV-002: mismatch with .env.example
semanticscholar,https://api.semanticscholar.org/graph/v1,api-key,0.1,1,10/600,BIOETL-SEMANTICSCHOLAR-API-KEY,ENV-001: mismatch with .env.example
```

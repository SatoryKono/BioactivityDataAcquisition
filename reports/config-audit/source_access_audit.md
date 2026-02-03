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
| ENV-001 | `.env.example:43` | `BIOETL_SEMANTIC_SCHOLAR_API_KEY` → `BIOETL_SEMANTICSCHOLAR_API_KEY` |
| CONFIG-001 | `configs/sources/pubmed.yaml:16-17` | `BIOETL_NCBI_*` → `BIOETL_PUBMED_*` |
| CONFIG-002 | `configs/pipelines/pubmed/publication.yaml:29-30` | `BIOETL_NCBI_*` → `BIOETL_PUBMED_*` |

---

## 1. Инвентаризация Конфигураций

### A. Таблица статуса доступа

| Provider | Base URL | Auth Type | Rate Limit (req/sec) | Circuit Breaker | Env Variables |
|----------|----------|-----------|----------------------|-----------------|---------------|
| ChEMBL | `https://www.ebi.ac.uk/chembl/api/data` | public | 3 | 5/300 | — |
| PubChem | `https://pubchem.ncbi.nlm.nih.gov/rest/pug` | public | 5 | 5/300 | — |
| UniProt | `https://rest.uniprot.org` | api_key | 10 (100 w/key) | 5/300 | `BIOETL_UNIPROT_API_KEY` |
| OpenAlex | `https://api.openalex.org` | email | 10 | 5/300 | `BIOETL_OPENALEX_EMAIL` |
| CrossRef | `https://api.crossref.org` | email | 50 | 5/300 | `BIOETL_CROSSREF_EMAIL` |
| PubMed | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | api_key | 3 (10 w/key) | 5/300 | `BIOETL_NCBI_API_KEY`, `BIOETL_NCBI_EMAIL` |
| SemanticScholar | `https://api.semanticscholar.org/graph/v1` | api_key | 0.1 (1 w/key) | **10/600** | `BIOETL_SEMANTICSCHOLAR_API_KEY` |

### B. Детализация по провайдерам

#### ChEMBL (`configs/sources/chembl.yaml`)
```yaml
# Lines 14-15, 30-32
base_url: https://www.ebi.ac.uk/chembl/api/data
auth_type: public
rate_limit:
  requests_per_second: 3
  burst: 10
```
**Статус:** OK — консервативный лимит для публичного API

#### PubChem (`configs/sources/pubchem.yaml`)
```yaml
# Lines 14-15, 27-29
base_url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
auth_type: public
rate_limit:
  requests_per_second: 5.0
  burst: 10
```
**Статус:** OK — соответствует документации (5 req/sec)

#### UniProt (`configs/sources/uniprot.yaml`)
```yaml
# Lines 14-16, 27-32
base_url: https://rest.uniprot.org
auth_type: api_key
api_key_env: BIOETL_UNIPROT_API_KEY
rate_limit:
  requests_per_second: 10.0
  burst: 20
  with_api_key:
    requests_per_second: 100
    burst: 200
```
**Статус:** OK — 10/100 req/sec соответствует документации

#### OpenAlex (`configs/sources/openalex.yaml`)
```yaml
# Lines 15-17, 31-34
base_url: https://api.openalex.org
auth_type: email
mailto: ${BIOETL_OPENALEX_EMAIL}
rate_limit:
  requests_per_second: 10
  burst: 20
  polite_pool: true
```
**Статус:** OK — 10 req/sec для polite pool

#### CrossRef (`configs/sources/crossref.yaml`)
```yaml
# Lines 15-17, 31-34
base_url: https://api.crossref.org
auth_type: email
mailto: ${BIOETL_CROSSREF_EMAIL}
rate_limit:
  requests_per_second: 50
  burst: 100
  polite_pool: true
```
**Статус:** OK — 50 req/sec для polite pool

#### PubMed (`configs/sources/pubmed.yaml`)
```yaml
# Lines 14-17, 31-36
base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
auth_type: api_key
api_key_env: BIOETL_NCBI_API_KEY
email_env: BIOETL_NCBI_EMAIL
rate_limit:
  requests_per_second: 3.0
  burst: 5
  with_api_key:
    requests_per_second: 10
    burst: 20
```
**Статус:** OK — 3/10 req/sec соответствует документации

#### SemanticScholar (`configs/sources/semanticscholar.yaml`)
```yaml
# Lines 21-23, 39-45
base_url: https://api.semanticscholar.org/graph/v1
auth_type: api_key
api_key: ${BIOETL_SEMANTICSCHOLAR_API_KEY}
circuit_breaker:
  failure_threshold: 10      # DEVIATION: 10 vs standard 5
  recovery_timeout: 600      # DEVIATION: 600 vs standard 300
rate_limit:
  requests_per_second: 0.1   # Very conservative
  burst: 1
  with_api_key:
    requests_per_second: 1.0
    burst: 5
```
**Статус:** OK — отклонения circuit breaker обоснованы (S2 API нестабилен)

---

## 2. Валидация Переменных Окружения

### CRITICAL: Несоответствия имён переменных

#### Issue #1: Semantic Scholar API Key
| Location | Variable Name | Status |
|----------|---------------|--------|
| `configs/sources/semanticscholar.yaml:23` | `BIOETL_SEMANTICSCHOLAR_API_KEY` | Config |
| `.env.example:42` | `BIOETL_SEMANTIC_SCHOLAR_API_KEY` | **MISMATCH** |
| `src/bioetl/composition/providers/registration.py:438` | `BIOETL_SEMANTICSCHOLAR_API_KEY` | Code |

**Проблема:** `.env.example` использует `BIOETL_SEMANTIC_SCHOLAR_API_KEY` (с underscore), но config и код — `BIOETL_SEMANTICSCHOLAR_API_KEY` (без underscore).

#### Issue #2: PubMed/NCBI Variables
| Location | Variable Name | Status |
|----------|---------------|--------|
| `configs/sources/pubmed.yaml:16-17` | `BIOETL_NCBI_API_KEY`, `BIOETL_NCBI_EMAIL` | Config |
| `configs/pipelines/pubmed/publication.yaml:29-30` | `BIOETL_NCBI_EMAIL`, `BIOETL_NCBI_API_KEY` | Pipeline |
| `.env.example:35-36` | `BIOETL_PUBMED_API_KEY`, `BIOETL_PUBMED_EMAIL` | **MISMATCH** |
| `.github/workflows/contract-tests.yml:77` | `BIOETL_PUBMED_API_KEY` | CI |
| `tests/contract/conftest.py:52` | `BIOETL_PUBMED_API_KEY` | Tests |

**Проблема:** Config использует `BIOETL_NCBI_*`, но `.env.example`, CI и тесты — `BIOETL_PUBMED_*`.

### OK: Корректные переменные

| Variable | Config | .env.example | Status |
|----------|--------|--------------|--------|
| `BIOETL_UNIPROT_API_KEY` | `uniprot.yaml:16` | `.env.example:43` | OK |
| `BIOETL_OPENALEX_EMAIL` | `openalex.yaml:17` | `.env.example:30` | OK |
| `BIOETL_CROSSREF_EMAIL` | `crossref.yaml:17` | `.env.example:10` | OK |

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

| Provider | failure_threshold | recovery_timeout | RULES.md (5/300) | Status |
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
    old_value: "BIOETL_SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key_here"
    new_value: "BIOETL_SEMANTICSCHOLAR_API_KEY=your_semantic_scholar_api_key_here"
    reason: "Несоответствие имени переменной с configs/sources/semanticscholar.yaml:23"

  - id: ENV-002
    severity: CRITICAL
    file: .env.example
    lines: 35-36
    old_value: |
      BIOETL_PUBMED_API_KEY=your_ncbi_api_key_here
      BIOETL_PUBMED_EMAIL=your_email@example.com
    new_value: |
      BIOETL_NCBI_API_KEY=your_ncbi_api_key_here
      BIOETL_NCBI_EMAIL=your_email@example.com
    reason: "Несоответствие с configs/sources/pubmed.yaml:16-17"
    note: "Также обновить CI workflow и тесты для консистентности"
```

### B. Альтернатива: Обновить configs вместо .env.example

Если тесты и CI уже используют `BIOETL_PUBMED_*`, можно обновить configs:

```yaml
alternative_corrections:
  - id: CONFIG-001
    file: configs/sources/pubmed.yaml
    lines: 16-17
    old_value: |
      api_key_env: BIOETL_NCBI_API_KEY
      email_env: BIOETL_NCBI_EMAIL
    new_value: |
      api_key_env: BIOETL_PUBMED_API_KEY
      email_env: BIOETL_PUBMED_EMAIL
    reason: "Согласование с CI и тестами"

  - id: CONFIG-002
    file: configs/pipelines/pubmed/publication.yaml
    lines: 29-30
    old_value: |
      email: "${BIOETL_NCBI_EMAIL}"
      api_key: "${BIOETL_NCBI_API_KEY}"
    new_value: |
      email: "${BIOETL_PUBMED_EMAIL}"
      api_key: "${BIOETL_PUBMED_API_KEY}"
```

---

## 6. Рекомендации

### Приоритет P1 (Critical)
1. Исправить несоответствие `BIOETL_SEMANTICSCHOLAR_API_KEY` в `.env.example`
2. Унифицировать `BIOETL_PUBMED_*` vs `BIOETL_NCBI_*` — выбрать один вариант

### Приоритет P2 (Medium)
1. Добавить валидацию env variables при старте pipeline
2. Создать скрипт проверки консистентности env vars

### Приоритет P3 (Low)
1. Документировать отклонение circuit breaker для SemanticScholar в ADR

---

## Артефакты

| Файл | Описание |
|------|----------|
| `source_access_audit.md` | Этот документ |
| `source_access_status.csv` | CSV таблица статусов (ниже) |

---

## Приложение: CSV Export

```csv
provider,base_url,auth_type,rate_limit_rps,rate_limit_with_key,circuit_breaker,env_vars,issues
chembl,https://www.ebi.ac.uk/chembl/api/data,public,3,—,5/300,—,—
pubchem,https://pubchem.ncbi.nlm.nih.gov/rest/pug,public,5,—,5/300,—,—
uniprot,https://rest.uniprot.org,api_key,10,100,5/300,BIOETL_UNIPROT_API_KEY,—
openalex,https://api.openalex.org,email,10,—,5/300,BIOETL_OPENALEX_EMAIL,—
crossref,https://api.crossref.org,email,50,—,5/300,BIOETL_CROSSREF_EMAIL,—
pubmed,https://eutils.ncbi.nlm.nih.gov/entrez/eutils,api_key,3,10,5/300,"BIOETL_NCBI_API_KEY,BIOETL_NCBI_EMAIL",ENV-002: mismatch with .env.example
semanticscholar,https://api.semanticscholar.org/graph/v1,api_key,0.1,1,10/600,BIOETL_SEMANTICSCHOLAR_API_KEY,ENV-001: mismatch with .env.example
```

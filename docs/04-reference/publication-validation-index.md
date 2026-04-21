---
Version: 1.0.1
Status: Production Ready ✅
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Publication Validation Documentation Index

**Дата:** 2026-03-20
**Статус:** Production Ready ✅

---

## Обзор

Комплексная система валидации публикационных данных BioETL, охватывающая **191 поле** из **5 провайдеров** (ChEMBL, PubMed, CrossRef, OpenAlex, Semantic Scholar) с **5-уровневой стратегией валидации**.

**Ключевые метрики и артефакты:**
- 📊 **191 поле** × 5 провайдеров
- ✅ **5 уровней валидации** (Base → Structural → External → Logical → Semantic)
- 🧪 **471 тест** (64% от целевых 735) по состоянию на 2026-02-06; актуальное покрытие проверяй по `tests/` и CI
- 📈 **Target DQ Pass Rate:** ≥ 95%

---

## Документация по категориям

### 🏛️ Архитектурные решения (ADR)

| Документ | Описание | Статус |
|----------|----------|--------|
| **[ADR-033](../02-architecture/decisions/ADR-033-publication-validation-strategy.md)** | Стратегия валидации публикаций: 5 уровней, DQ-флаги, карантин, конфигурация | ✅ Принят (2026-02-06) |

**Связанные ADR:**
- [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) — Hexagonal Architecture (validation services в application layer)
- [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) — Medallion Architecture (Bronze → Silver → Gold)
- [ADR-027](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) — Silver Layer DQ Framework (`-dq-warn`, `-dq-error`)

---

### 📖 Справочники

| Документ | Описание | Охват |
|----------|----------|-------|
| **[Publication Fields Reference](publication-fields-reference.md)** | Historical/source artifact from older spreadsheet inventory; not the canonical publication contract | Historical only |
| **[Validation Schema v3](schemas/publication_validation_schema_v3.xlsx)** | Supporting validation-rules matrix (XLSX + CSV export); canonical field names and aliases still live in provider refs and `configs/entities/{provider}/publication.yaml` | 191 правил × 5 уровней |
| **[Glossary v2.5](../00-project/glossary.md)** | Ubiquitous Language: термины валидации, DQ-флаги, режимы | 12 новых терминов |

---

### 📚 Руководства

| Документ | Целевая аудитория | Содержание |
|----------|-------------------|------------|
| **[Validation Guide](../03-guides/publication-validation-guide.md)** | Data Engineers, Developers | Полное руководство по реализации с 4 Mermaid-диаграммами, примерами кода, best practices |
| **[Operational Runbook](../05-operations/runbooks/publication-validation-runbook.md)** | DevOps, Support, On-Call | Диагностика сбоев, bash-команды, escalation path, контакты провайдеров |

---

### 🧪 Тесты

| Документ | Описание | Покрытие |
|----------|----------|----------|
| **[Contract Tests README](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/tests/contract/silver_schemas/README.md)** | Описание контрактных тестов и snapshot-процесса | Contract tests |
| **[Publication Schema Contracts](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/tests/contract/test_publication_schema_contracts.py)** | Тесты валидации схем публикаций | Contract tests |

**Test Organization:**
```
tests/
├── contract/
│   ├── silver_schemas/README.md    # Contract test docs
│   └── test_publication_schema_contracts.py
├── unit/domain/schemas/            # Base validation tests
├── unit/application/services/dq/   # Structural/logical/semantic tests
├── integration/validation/         # External verification tests (VCR)
└── test-coverage-matrix.csv        # Coverage report
```

---

## Quick Start

### 1. Понять архитектуру

```bash
# Прочитать ADR-033 (решение + обоснование)
open docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md

# Изучить диаграммы в Validation Guide
open docs/03-guides/publication-validation-guide.md
```

**Диаграммы:**
- 🏗️ Компонентная архитектура (Adapter → Pandera → 4 validators → Delta Lake)
- 🔄 Жизненный цикл DQ-флагов (state machine)
- ⚙️ Иерархия конфигурации (Default → Provider → Pipeline → CLI)
- 📊 End-to-End workflow (sequence diagram)

---

### 2. Найти поле

```bash
# Проверить provider-specific canonical reference
open docs/04-reference/providers/chembl/publication.md

# Или поискать в валидационной схеме
grep "pmid" docs/04-reference/schemas/publication_validation_schema_v3.csv
```

**Пример записи:**
```
field-name: pubmed.publication.pmid
data-type: string
is-nullable: non-nullable
base-validation: regex: ^[1-9]\d*$ (positive integer)
base-result: FAIL
external-verification: PubMed/NCBI API
```

---

### 3. Запустить валидацию

```bash
# Полный прогон со стандартным run command
bioetl run --pipeline pubmed_publication \
  --limit 500

# Баланс скорость/качество (дефолтные уровни из pipeline config)
bioetl run --pipeline chembl_publication \
  --limit 1000

# Быстрый сухой прогон схемы (без записи)
bioetl run --pipeline crossref_publication \
  --limit 200 \
  --dry-run
```

> Примечание: отдельного `--run-type validation` в текущем CLI нет; глубина
> validation определяется pipeline config, schema hooks и dry-run / limit
> режимами стандартной команды `bioetl run`.

---

### 4. Запустить тесты

```bash
# Все тесты
pytest tests/contract/ -v

# По маркерам
pytest tests/contract/ -m unit           # Unit tests only
pytest tests/contract/ -m integration    # Integration tests only
pytest tests/contract/ -m contracts      # Contract tests only

# По провайдеру
pytest tests/contract/ -k pubmed -v

# С coverage
pytest tests/contract/ --cov=src/bioetl --cov-report=html
```

---

### 5. Диагностировать проблемы

```bash
# Открыть Operational Runbook
open docs/05-operations/runbooks/publication-validation-runbook.md

# Проверить последние ошибки валидации
tail -200 reports/logs/bioetl.log | jq 'select(.event == "validation-failed")'

# Топ провайдеров по fail rate
cat reports/logs/bioetl.log | \
  jq -r 'select(.event == "validation-failed") | "\(.provider) \(.validation-level)"' | \
  sort | uniq -c | sort -rn | head -10
```

---

## Workflow по ролям

### Data Engineer (Реализация)

1. **Прочитать:**
   - [ADR-033](../02-architecture/decisions/ADR-033-publication-validation-strategy.md) — Архитектурное решение
   - [Validation Guide](../03-guides/publication-validation-guide.md) — Примеры кода

2. **Реализовать:**
   - Добавить Pandera checks в Silver schema
   - Реализовать StructuralValidator / LogicalValidator
   - Интегрировать в трансформер

3. **Тестировать:**
    - Запустить `pytest tests/contract/` — проверить существующие тесты
   - Добавить provider-specific tests по примерам

4. **Документировать:**
   - Обновить provider-specific reference page в `docs/04-reference/providers/{provider}/publication.md`
   - Синхронизировать aliases/contracts в `configs/entities/{provider}/publication.yaml`
   - Добавить правила в [Validation Schema](schemas/publication_validation_schema_v3.xlsx)

---

### DevOps / Support (Эксплуатация)

1. **Настроить мониторинг:**
   - Prometheus metrics: `bioetl_dq_validation_score`, `bioetl_dq_records_quarantined_total`, `bioetl_dq_validation_failures_total`, `bioetl_dq_check_duration_ms`
   - Grafana dashboard: DQ Score, Quarantine Rate, Hard-Fail Events, Validation Latency

2. **При алерте:**
   - Открыть [Operational Runbook](../05-operations/runbooks/publication-validation-runbook.md)
   - Следовать процедурам диагностики по уровням валидации
   - Использовать bash-команды для troubleshooting

3. **Escalation:**
   - Level 1: Self-Service (0-30 min) — runbook
   - Level 2: Team Slack (30 min - 2 hours) — `#bioetl-support`
   - Level 3: On-Call Engineer (2-4 hours) — PagerDuty
   - Level 4: Data Engineering Lead (4+ hours) — email

---

### QA / Test Engineer (Тестирование)

1. **Изучить тесты:**
    - [Contract Tests README](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/tests/contract/silver_schemas/README.md)
    - [Publication Schema Contracts](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/tests/contract/test_publication_schema_contracts.py)

2. **Расширить покрытие:**
   - Base Validation: добавить edge cases для string fields (empty, whitespace, very long)
   - Structural Validation: добавить сценарии для всех 25 структурных правил
   - External Verification: заменить mocks на VCR cassettes

3. **Target coverage:**
   - Base: 500 tests (сейчас 329 — **66%**)
   - Structural: 80 tests (сейчас 16 — **20%**)
   - External: 40 tests (сейчас 16 — **40%**)
   - Logical: 60 tests (сейчас 12 — **20%**)
   - Semantic: 30 tests (сейчас 13 — **43%**)

---

## Расширение системы

### Добавление нового провайдера

1. Определить поля в Pandera schema (`src/bioetl/domain/schemas/{provider}/publication.py`)
2. Добавить правила в `publication_validation_schema_v3.xlsx`
3. Сгенерировать тесты из XLSX (автоматический генератор не зафиксирован в репозитории; выполнять вручную по шаблонам `tests/contract/`)
4. Обновить provider-specific publication reference page и `field_aliases`/contracts для нового провайдера
5. Добавить провайдера в конфигурацию External Verification

---

### Добавление нового уровня валидации

1. Создать validator класс в `application/services/dq/`
2. Реализовать `validate(df: pd.DataFrame) -> pd.DataFrame` метод
3. Интегрировать в pipeline workflow (после LogicalValidator)
4. Добавить конфигурацию в `application/config/validation.yaml`
5. Написать unit tests (`tests/unit/application/services/dq/`)
6. Обновить [Validation Guide](../03-guides/publication-validation-guide.md) с описанием уровня

---

### Добавление нового правила

1. **Для Base Validation:**
   - Добавить Pandera `Field()` с regex/check
   - Написать parametrized test

2. **Для Structural Validation:**
   - Добавить метод в `StructuralValidator`
   - Написать PASS/WARN сценарии

3. **Для Logical Validation:**
   - Добавить метод в `LogicalValidator`
   - Написать parametrized test с граничными значениями

4. **Для Semantic Validation:**
   - Добавить NLP check в `SemanticValidator`
   - Mock NLP модель в тестах

---

## Связанные ресурсы

### Внутренние

- **RULES.md** — `docs/00-project/RULES.md` (§8 Testing, §9 Anti-Patterns)
- **CLAUDE.md** — `docs/00-project/ai/agents/guides/CLAUDE.md` (§7.5 Type Annotations, §9 Anti-Patterns)
- **CI/CD Pipeline** — `.github/workflows/tests.yml`

### Внешние (Upstream Providers)

| Провайдер | API Docs | Status Page | Rate Limit |
|-----------|----------|-------------|------------|
| **CrossRef** | https://api.crossref.org/ | https://status.crossref.org/ | 50 req/s (polite pool) |
| **PubMed** | https://www.ncbi.nlm.nih.gov/books/NBK25501/ | https://www.ncbi.nlm.nih.gov/home/about/policies/ | 3 req/s (no key), 10 req/s (with key) |
| **OpenAlex** | https://docs.openalex.org/ | https://status.openalex.org/ | 100,000 req/day (polite pool) |
| **Semantic Scholar** | https://api.semanticscholar.org/ | — | 100 req/5min |
| **ChEMBL** | https://www.ebi.ac.uk/chembl/api/data/docs | — | No official limit |

### Инструменты

- **Pandera** — https://pandera.readthedocs.io/ (Base Validation framework)
- **VCR.py** — https://vcrpy.readthedocs.io/ (HTTP recording/replay для integration tests)
- **pytest** — https://docs.pytest.org/ (Test framework)
- **structlog** — https://www.structlog.org/ (Structured logging)

---

## Статистика

| Метрика | Значение | Target |
|---------|----------|--------|
| **Полей** | 191 | — |
| **Провайдеров** | 5 | — |
| **Уровней валидации** | 5 | — |
| **Тестов** | 471 | 735 (64%) |
| **Документов** | 7 | — |
| **Диаграмм** | 4 Mermaid | — |
| **Bash команд** | 50+ | — |
| **DQ Pass Rate** (baseline) | 72% | 95% |

---

## Timeline

| Дата | Событие |
|------|---------|
| **2026-02-06** | ✅ Утверждение ADR-033 |
| **2026-02-06** | ✅ Генерация Validation Schema v3 (191 правило) |
| **2026-02-06** | ✅ Генерация Test Suite (471 тест, 64% покрытие) |
| **2026-02-06** | ✅ Публикация документации (7 документов) |
| **2026-02-10** | 🔜 Реализация External Verification с VCR cassettes |
| **2026-02-15** | 🔜 Достижение 85% test coverage (625 тестов) |
| **2026-02-20** | 🔜 Production deployment с Strict Mode |
| **2026-03-01** | 🔜 DQ Pass Rate ≥ 95% |

---

## Контакты

- **Maintainers:** см. `CODEOWNERS`
- **Support:** `#bioetl-support` (Slack)
- **On-Call:** `#bioetl-oncall` (Slack)

---

**Версия документа:** 1.0.0
**Последнее обновление:** 2026-02-06
**Владелец:** Data Engineering Team
**Статус:** Production Ready ✅

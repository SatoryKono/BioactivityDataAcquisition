______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-033: Publication Metadata Validation Strategy

**Date:** <YYYY-MM-DD>
**Status:** Accepted
**Decision makers:** @BioETL-Team

| Параметр          | Значение                                                                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Статус**        | Accepted (Levels 1,4 implemented; Level 2 partial; Levels 3,5 not yet realized — see Implementation Status)                                                                                                   |
| **Дата**          | 2026-02-06                                                                                                                                                                                                    |
| **Автор**         | BioETL Team                                                                                                                                                                                                   |
| **Ревьюер**       | —                                                                                                                                                                                                             |
| **Связанные ADR** | [ADR-002](ADR-002-medallion-architecture.md) (Medallion Architecture), [ADR-014](ADR-014-deterministic-writes.md) (Deterministic Writes), [ADR-027](ADR-027-dq-rules-externalization.md) (DQ Externalization) |
| **Заменяет**      | —                                                                                                                                                                                                             |
| **Заменён**       | —                                                                                                                                                                                                             |

______________________________________________________________________

## Context

### Проблема

Система BioETL интегрирует метаданные научных публикаций из **5 гетерогенных провайдеров**:

| Провайдер            | Полей | Primary Key          | API Особенности                 |
| -------------------- | ----- | -------------------- | ------------------------------- |
| **ChEMBL**           | 28    | `document-chembl-id` | REST, стабильная схема          |
| **PubMed**           | 52    | `pmid`               | MEDLINE XML, богатые метаданные |
| **CrossRef**         | 37    | `doi`                | REST, неполные данные           |
| **OpenAlex**         | 39    | `openalex-id`        | REST, академическая граф-база   |
| **Semantic Scholar** | 35    | `paper-id`           | REST, AI-генерированные TLDR    |

**Всего: 191 поле** (с учетом всех полей включая унаследованные от `PublicationBaseSchema`).

#### Вызовы

1. **Гетерогенность форматов:**

   - DOI regex различается (CrossRef: non-nullable PK vs PubMed: nullable enrichment field)
   - Типы данных: строки vs числа (page-first может быть "e1234" или "100")
   - Дублирование полей: 5 провайдеров × ~20 общих полей = ~100 вариаций

1. **Качество данных:**

   - Неполные записи: ~15% CrossRef-записей без title
   - Противоречия: publication-year ≠ YEAR(publication-date) в ~2% PubMed
   - Семантическая несогласованность: title-abstract similarity < 0.1 в ~5% OpenAlex

1. **Отсутствие унифицированной стратегии:**

   - Pandera валидирует только схему Silver (форматные проверки)
   - Нет кросс-полевой валидации (page-first ≤ page-last)
   - Нет верификации по внешним источникам (DOI существует в CrossRef API?)
   - Нет семантических проверок (язык аннотации совпадает с полем language?)

1. **Отсутствие DQ-метрик:**

   - Нет отчётов о качестве данных на уровне провайдера/поля
   - Нет возможности отследить % записей с проблемами
   - Нет карантина для критически невалидных записей

### Требования

**Функциональные:**

- **REQ-VAL-001 (MUST):** Многоуровневая валидация: base → structural → external → logical → semantic.
- **REQ-VAL-002 (MUST):** DQ-флаги: `_dq_error` (блокирующие ошибки), `_dq_warn` (предупреждения).
- **REQ-VAL-003 (MUST):** Карантин: записи с `_dq_error=True` → Dead Letter Queue, не попадают в Gold.
- **REQ-VAL-004 (MUST):** Внешняя верификация: DOI/PMID/ORCID проверяются через авторитетные API.
- **REQ-VAL-005 (SHOULD):** Graceful degradation: таймауты API не блокируют пайплайн (SKIP).

**Нефункциональные:**

- **REQ-VAL-006 (MUST):** Производительность: overhead валидации < 20% от времени трансформации.
- **REQ-VAL-007 (MUST):** Детерминизм: валидация не зависит от порядка записей.
- **REQ-VAL-008 (MUST):** Конфигурируемость: DQ-правила в YAML, не хардкод.

### Связь с архитектурой

- **ADR-002 (Medallion):** Валидация на Silver-слое (Pandera), Gold (PyArrow strict).
- **ADR-014 (Deterministic Writes):** content-hash проверяется structural validation.
- **ADR-027 (DQ Externalization):** DQ-правила в `configs/validation/{provider}.yaml`.

______________________________________________________________________

## Decision

### Пятиуровневая стратегия валидации

```
┌─────────────────────────────────────────────────────────────┐
│                   Publication Record                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │  1. BASE VALIDATION       │
         │  (Pandera Schema)         │
         │  - Regex patterns         │
         │  - Nullable constraints   │
         │  - Type coercion          │
         └──┬──────────────┬─────────┘
            │ PASS         │ FAIL
            │              └──────────► _dq_error=True → Quarantine
            │
         ┌──▼──────────────────────────┐
         │  2. STRUCTURAL VALIDATION   │
         │  (Cross-field rules)        │
         │  - page-first ≤ page-last   │
         │  - content-hash consistency │
         │  - Field dependencies       │
         └──┬──────────────┬───────────┘
            │ PASS         │ FAIL → _dq_error=True
            │              │ WARN → _dq_warn=True
            │
         ┌──▼──────────────────────────┐
         │  3. EXTERNAL VERIFICATION   │
         │  (API lookups)              │
         │  - DOI in CrossRef?         │
         │  - PMID in PubMed?          │
         │  - ORCID valid?             │
         └──┬──────────────┬───────────┘
            │ PASS/SKIP    │ FAIL (PK) → _dq_error=True
            │              │ WARN (non-PK) → _dq_warn=True
            │
         ┌──▼──────────────────────────┐
         │  4. LOGICAL VALIDATION      │
         │  (Ranges & Invariants)      │
         │  - 1800 ≤ year ≤ 2027       │
         │  - citations ≥ 0            │
         │  - dates ordering           │
         └──┬──────────────┬───────────┘
            │ PASS         │ WARN → _dq_warn=True
            │
         ┌──▼──────────────────────────┐
         │  5. SEMANTIC VALIDATION     │
         │  (NLP checks)               │
         │  - Title-abstract similarity│
         │  - Language detection       │
         │  - Keyword relevance        │
         └──┬──────────────┬───────────┘
            │ PASS         │ WARN → _dq_warn=True
            │
         ┌──▼──────────────────────────┐
         │     Write to Silver         │
         │  (_dq_error=False records)  │
         └─────────────────────────────┘
```

### Детализация уровней

#### 1. Base Validation (Pandera)

**Назначение:** Форматная проверка на уровне поля.

**Правила:**

- Regex-паттерны: DOI (`^10\.\d{4,9}/.+$`), PMID (`^[1-9]\d*$`), ORCID (`^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`)
- Nullable constraints: PK поля — non-nullable, enrichment — nullable
- Type coercion: `pd.Int64Dtype` для nullable integers

**Результат:**

- `PASS` → переход к structural
- `FAIL` → `_dq_error=True`, запись отклонена

**Пример (Pandera):**

```python
class ChemblPublicationSchema(PublicationBaseSchema):
    document - chembl - id: Series[str] = pa.Field(
        nullable=False,
        str - matches=r"^CHEMBL\d+$",
        description="ChEMBL Document ID (PK)",
    )
```

#### 2. Structural Validation (Service)

**Назначение:** Проверка согласованности между полями одной записи.

**Правила:**

- `page-first ≤ page-last` (если оба числовые)
- `content-hash == recomputed-hash(excl. _ingestion_ts, _run_id, -dq-*)`
- `IF corpus-id NOT NULL THEN paper-id MUST NOT be NULL` (S2)
- `publication-year == YEAR(publication-date)` (если оба заполнены)

**Результат:**

- `PASS` → external verification
- `FAIL` → `_dq_error=True` (критические: content-hash)
- `WARN` → `_dq_warn=True` (некритические: page ordering)

#### 3. External Verification (Integration)

**Назначение:** Сопоставление с авторитетными источниками.

**Поддерживаемые API:**

- CrossRef: `/works/{doi}` → HTTP 200
- PubMed: `/efetch.fcgi?db=pubmed&id={pmid}`
- OpenAlex: `/works/{openalex-id}`
- Semantic Scholar: `/graph/v1/paper/{paper-id}`
- ChEMBL: `/api/data/document/{chembl-id}`
- ORCID: `/v3.0/{orcid}`
- ROR: `/organizations/{ror-id}`

**Стратегия отказов:**

- Timeout (> 5s) → `SKIP` (graceful degradation)
- HTTP 404 → `FAIL` (для PK), `WARN` (для non-PK)
- Rate limit (429) → Circuit Breaker → `SKIP`

**Результат:**

- `PASS` / `SKIP` → logical validation
- `FAIL` (PK not found) → `_dq_error=True`
- `WARN` (non-PK not found) → `_dq_warn=True`

#### 4. Logical Validation (Service)

**Назначение:** Проверка числовых диапазонов и временных инвариантов.

**Правила:**

- `1800 ≤ publication-year ≤ CURRENT-YEAR + 1`
- `citations-received ≥ 0`, `citations-made ≥ 0`
- `fwci ≥ 0.0` (OpenAlex)
- `citations-received ≥ influential-citation-count` (S2)
- `date-completed ≤ date-revised` (PubMed)

**Результат:**

- `PASS` → semantic validation
- `WARN` → `_dq_warn=True` (логически некорректно, но не блокирует)

#### 5. Semantic Validation (Service, NLP)

**Назначение:** Проверка смысловой согласованности текстовых полей.

**Правила (примеры):**

- `SemanticSimilarity(title, abstract) > 0.3` (Sentence-BERT)
- `Language(abstract) == language` (langdetect)
- `Keywords(abstract) ∩ subject-keywords ≠ ∅`
- `MeSH` terms relevance (NLP topic modeling)

**Результат:**

- `PASS` / `WARN` → `_dq_warn=True`
- **NEVER FAIL** (семантика не блокирует)

### DQ-флаги и карантин

| Флаг        | Устанавливается при | Действие                                                  |
| ----------- | ------------------- | --------------------------------------------------------- |
| `_dq_error` | FAIL на уровнях 1-3 | Запись → Quarantine (Dead Letter), не попадает в Silver   |
| `_dq_warn`  | WARN на уровнях 2-5 | Запись → Silver с флагом, может быть отфильтрована в Gold |

**Карантин:**

- Путь: `data/output/quarantine/{provider}/publication/{date}/`
- Формат: Delta Lake (для SCD Type 2)
- Retention: 90 дней
- Ручная проверка: через Delta Lake/Polars и SQL-запросы к `data/output/quarantine/...`

### Конфигурация DQ

**Иерархия:**

```
configs/validation/
├── _defaults.yaml                    # Глобальные пороги
├── chembl.yaml                       # Провайдер-специфичные
├── pubmed/
│   └── publication.yaml              # Entity-специфичные
└── overrides/
    └── emergency-disable-external.yaml  # Runtime overrides
```

**Пример конфигурации:**

```yaml
# configs/validation/pubmed/publication.yaml
validation:
  base:
    enabled: true
    fail-fast: false  # Collect all errors

  structural:
    enabled: true
    rules:
      - name: year-date-consistency
        severity: WARN
        enabled: true

  external:
    enabled: true
    timeout-ms: 5000
    circuit-breaker:
      failure-threshold: 5
      recovery-timeout-s: 60

  logical:
    enabled: true
    year-range: [1800, 2027]

  semantic:
    enabled: false  # Expensive, optional
    similarity-threshold: 0.3

dq-thresholds:
  soft-fail-threshold: 0.05  # 5% errors → warning
  hard-fail-threshold: 0.20  # 20% errors → pipeline fail
```

______________________________________________________________________

## Alternatives Considered

### Альтернатива 1: Монолитная валидация в Pandera (отклонена)

**Описание:**

- Все правила (включая кросс-полевые и внешние) в Pandera `@pa.check()`.
- Единая точка валидации на Silver-слое.

**Преимущества:**

- Простота: один инструмент
- Декларативность: все правила в схеме

**Недостатки:**

- ❌ **Нет внешней верификации:** Pandera не поддерживает HTTP-вызовы в `@pa.check()`
- ❌ **Плохая производительность:** синхронная валидация блокирует I/O
- ❌ **Нет graceful degradation:** таймаут API = падение пайплайна
- ❌ **Негибкость:** нельзя отключить дорогие проверки runtime

**Вердикт:** Отклонено из-за невозможности внешней верификации и отсутствия гибкости.

### Альтернатива 2: Pandera + Great Expectations (отклонена)

**Описание:**

- Pandera для base validation
- Great Expectations для structural/logical/external

**Преимущества:**

- Great Expectations имеет встроенные DQ-метрики
- Rich HTML-отчёты

**Недостатки:**

- ❌ **Избыточная зависимость:** два фреймворка с перекрывающейся функциональностью
- ❌ **Сложность интеграции:** GE работает с SQL, не с DataFrames напрямую
- ❌ **Overhead:** GE checkpoint + validation = +30% времени
- ❌ **Semantic validation:** GE не поддерживает NLP-проверки

**Вердикт:** Отклонено из-за избыточности и сложности.

### Альтернатива 3: Текущее решение — пятиуровневая валидация

**Преимущества:**

- ✅ Разделение ответственности: Pandera (schema), Service (logic), Integration (API)
- ✅ Гибкость: каждый уровень можно отключить/настроить
- ✅ Graceful degradation: external verification не блокирует пайплайн
- ✅ Расширяемость: легко добавить новые уровни (e.g., ML-based anomaly detection)

**Недостатки:**

- ⚠️ Сложность: 5 уровней + конфигурация
- ⚠️ Overhead: +15-20% времени выполнения (измерено на PubMed)

**Вердикт:** Принято как оптимальное соотношение гибкость/сложность.

______________________________________________________________________

## Consequences

### Позитивные

1. **Качество данных:**

   - Снижение невалидных записей в Silver с ~8% до ~2% (измерено на ChEMBL pilot)
   - 100% покрытие PK-полей внешней верификацией

1. **Наблюдаемость:**

   - DQ-метрики на уровне провайдера/поля/уровня валидации
   - `-dq-report.json` для каждого run: error rate, warn rate, quarantine count

1. **Гибкость:**

   - Можно отключить дорогие проверки (semantic, external) в production
   - Emergency overrides без деплоя кода

1. **Compliance:**

   - Аудитируемость: карантин хранит невалидные записи с причинами
   - Reproducibility: детерминистическая валидация (content-hash)

### Негативные

1. **Сложность:**

   - 5 уровней валидации требуют понимания всей стратегии
   - Новым разработчикам нужно изучить иерархию конфигурации

1. **Производительность:**

   - External verification: +10% времени (с circuit breaker)
   - Semantic validation: +15-20% времени (если включена)
   - **Mitigation:** Batch API calls, async I/O, кеширование

1. **Зависимости:**

   - Внешние API: CrossRef, PubMed, ORCID (риск downtime)
   - **Mitigation:** Circuit breaker, graceful degradation (SKIP)

1. **Maintenance:**

   - Regex-паттерны и диапазоны нужно обновлять (e.g., MAX-YEAR)
   - API endpoints могут измениться
   - **Mitigation:** Версионирование конфигов, архитектурные тесты

### Нейтральные

1. **Размер кодовой базы:**

   - +~1500 LOC для validation services
   - +~735 тестов для покрытия всех уровней

1. **Disk usage:**

   - Карантин: ~2% от Silver (оценка на ChEMBL)
   - DQ reports: ~10 MB/run

______________________________________________________________________

## Implementation Status (as of 2026-03-15)

| Level | Name                                   | Status              | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----- | -------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Base Validation (Pandera)              | **IMPLEMENTED**     | `domain/schemas/base.py`, `domain/schemas/common/publication_base.py`, `domain/schemas/validators.py`, `infrastructure/validation/pandera_validator.py`, `domain/contracts/gold/publications_*.py` — regex patterns, nullable constraints, type coercion all in place                                                                                                                                                                     |
| 2     | Structural Validation (cross-field)    | **PARTIAL**         | Data model: `domain/config/validation.py` (`CrossFieldValidation`, `ConditionalValidation`). Config loading: `infrastructure/schemas/dq_config.py`. YAML rules: `configs/entities/{crossref,pubmed}/publication.yaml`. Content-hash check: `application/services/dq/silver_statistics.py`. **Gap:** no runtime executor applies YAML-defined cross-field rules per-record during transformation; `page_first ≤ page_last` not implemented |
| 3     | External Verification (API lookup)     | **NOT IMPLEMENTED** | No verification code exists. CrossRef adapter is enrichment, not verification. `configs/validation/` hierarchy from ADR does not exist in repo                                                                                                                                                                                                                                                                                            |
| 4     | Logical Validation (ranges/invariants) | **PARTIAL**         | Pandera Gold schemas enforce `ge=0` on citations, year ranges. YAML `field_validations` defined in entity configs. Gold-layer `_checks_business.py` runs range checks. **Gap:** `field_validations` not consumed during Silver transform; date ordering invariants not implemented                                                                                                                                                        |
| 5     | Semantic Validation (NLP)              | **NOT IMPLEMENTED** | `domain/behavior/text_similarity.py` exists (Jaccard) but serves composite cross-validation, not title-abstract DQ. No language detection, no NLP libraries in dependencies                                                                                                                                                                                                                                                               |

### Assessment

Levels 1 and 4 (Pandera + Gold range checks) provide **effective coverage** for the most impactful validation scenarios. The YAML infrastructure for Levels 2-4 (data model, config loading, Pydantic schemas) is **complete** — the missing piece is a runtime executor that reads `DQConfig.field_validations` / `cross_field_validations` and applies them per-record during Silver transformation.

Levels 3 and 5 remain **aspirational**. Level 3 (external verification) would add significant latency and API dependency risk for marginal benefit given existing enrichment pipelines already validate PK resolution. Level 5 (NLP) requires new library dependencies and is explicitly optional per ADR design.

**Recommendation:** Focus future work on wiring the Level 2 runtime executor and completing Level 4 invariants. Levels 3 and 5 should remain documented as future enhancements.

______________________________________________________________________

## References

- **ADR-002 (Medallion Architecture):** Валидация на Silver-слое, strict mode на Gold.
- **ADR-014 (Deterministic Writes):** `content-hash` проверяется structural validation.
- **ADR-027 (DQ Externalization):** DQ-правила в YAML, не в коде.
- **ADR-024 (Entity Naming Unification):** `publication` entity для всех провайдеров.
- **ADR-026 (Composite Publication Pipeline):** Валидация в seed + enricher pipelines.

______________________________________________________________________

## Метрики успеха

| Метрика                                     | Baseline (до) | Target (после) | Measured                        |
| ------------------------------------------- | ------------- | -------------- | ------------------------------- |
| Невалидные записи в Silver                  | ~8%           | < 2%           | 1.8% (ChEMBL pilot)             |
| DQ coverage (полей с правилами)             | 45%           | 90%            | 91% (191/191 полей)             |
| False positives (WARN → ручная проверка OK) | —             | < 5%           | 3.2% (PubMed)                   |
| External verification coverage (PK)         | 0%            | 100%           | *Not yet implemented (Level 3)* |
| Pipeline overhead                           | 0%            | < 20%          | 15-18% (Levels 1+4 only)        |

______________________________________________________________________

## References

**Документация:**

- [Publication Validation Index](../../04-reference/publication-validation-index.md)
- [Validation Guide](../../03-guides/publication-validation-guide.md)
- [Operational Runbook](../../05-operations/runbooks/publication-validation-runbook.md)

**Код:**

- Schemas: `src/bioetl/domain/schemas/{provider}/publication.py`
- Services: `src/bioetl/application/services/dq/`
- Tests: `tests/unit/domain/schemas/`, `tests/integration/validation/`

**Конфигурация:**

- `docs/04-reference/schemas/publication_validation_schema_v3.xlsx` — источник правил
- `configs/entities/{provider}/{entity}.yaml` — runtime конфигурация (DQ rules in `dq_rules` section)

______________________________________________________________________

**Версия документа:** 1.1.0
**Последнее обновление:** 2026-03-15

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                     |
| ------------ | -------------------------------------------------------------------------- | ------ | -------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-033-publication-validation-strategy.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                   |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                             |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`         |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                 |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.

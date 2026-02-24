# Architecture Audit Report — Code Duplication Consolidation

Date: 2026-02-24  
Scope: `src/bioetl/application/**`, `src/bioetl/infrastructure/adapters/**`, зависимые factory/tests  
Requested branches: `codex/analyze-code-duplication-and-extract-logic`, `codex/analyze-code-duplication-and-extract-logic-qds3s7`, `codex/analyze-code-duplication-and-extract-logic-n50rpx`

## Executive Summary

- Total findings: **2**
- Critical (MUST): **0**
- Moderate (SHOULD): **0**
- Informational (MAY): **2**
- Потенциальное сокращение шаблонного кода: **~55-120 LOC** (без изменения business semantics).

## Consolidation Status (requested branches)

- `git branch --all` в текущем окружении содержит только рабочую ветку (`work`), без запрошенных веток.
- Поэтому выполнена консолидация по **доступным артефактам и исходному коду** с пометкой:
  - **Requires Manual Review**: сверка с отсутствующими branch refs при их публикации/доступе.

## Dependency Maps (RULES §14 protocol)

### Map A — publication transformer constructors (`__init__` passthrough)

#### Importers

- `src/bioetl/composition/factories/pipeline_factories.py` — импортирует publication transformers и регистрирует их как `transformer_class`.
- `src/bioetl/composition/factories/transformer_factory.py` — импортирует те же классы для DI-фабрики.
- `src/bioetl/application/pipelines/{openalex,crossref,pubmed,semanticscholar}/__init__.py` — re-export.

#### Users

- `tests/architecture/test_transformer_signatures.py` — валидирует сигнатуры и inheritance.
- Unit/integration tests публикационных трансформеров (OpenAlex/CrossRef/PubMed/S2).

#### Migration Order

1. Сначала обновить `BasePublicationTransformer` (если вводятся class-level defaults).
2. Затем упростить `__init__` в OpenAlex/CrossRef/S2.
3. PubMed оставить отдельным (stateful init).
4. Обновить architecture tests сигнатур.

### Map B — selector hooks (`_get_primary_id_field`, `_get_entity_class`)

#### Importers / Users

- `BasePublicationTransformer._transform_impl()` вызывает `_get_primary_id_field()` и `_get_entity_class()` в Template Method потоке.

#### Tests

- `tests/unit/application/pipelines/common/test_base_publication_transformer.py`
- `tests/architecture/test_transformer_signatures.py`

#### Migration Order

1. Ввести class attrs в base (`PRIMARY_ID_FIELD`, `ENTITY_CLASS`) опционально.
2. Перевести publication transformers на декларативные attrs.
3. Сохранить backward-compatible hooks в переходный период.

## Findings

## [Informational (P3)] Repeated passthrough `__init__` in publication transformers

**Location**:
- `src/bioetl/application/pipelines/openalex/transformer.py:83-122`
- `src/bioetl/application/pipelines/crossref/transformer.py:68-107`
- `src/bioetl/application/pipelines/semanticscholar/transformer.py:83-122`
- Counter-example: `src/bioetl/application/pipelines/pubmed/transformer.py:88-130`

**Rule**: DRY optimization opportunity (MAY), not an architecture violation.

**Evidence**:

```python
# openalex
super().__init__(
    provider,
    entity_type=entity_type,
    tracer=tracer,
    metrics=metrics,
    silver_filters=silver_filters,
    gold_filters=gold_filters,
    identity_service=identity_service,
    pii_hasher=pii_hasher,
    data_normalizer=data_normalizer,
    contract_policy=contract_policy,
)
```

```python
# pubmed (semantic difference)
super().__init__(...)
self._cached_xml_root = None
self._author_extractor = AuthorExtractor()
self._date_extractor = DateExtractor()
```

**Impact**: низкий; снижает только boilerplate, не меняет runtime поведение.

**Recommendation**:

```python
# BasePublicationTransformer (possible)
DEFAULT_PROVIDER: ClassVar[str]
DEFAULT_ENTITY_TYPE: ClassVar[str] = "publication"
```

Сократить passthrough-конструкторы только там, где нет provider-specific state.

**Verification command**:  
`rg "def __init__\(" src/bioetl/application/pipelines/{openalex,crossref,semanticscholar,pubmed}/transformer.py -n`

---

## [Informational (P3)] Repeated selector hook methods in publication transformers

**Location**:
- OpenAlex: `src/bioetl/application/pipelines/openalex/transformer.py:293-309`
- CrossRef: `src/bioetl/application/pipelines/crossref/transformer.py:240-256`
- PubMed: `src/bioetl/application/pipelines/pubmed/transformer.py:503-519`
- SemanticScholar: `src/bioetl/application/pipelines/semanticscholar/transformer.py:272-288`
- Hook usage in base flow: `src/bioetl/application/pipelines/common/base_publication_transformer.py:202-203`

**Rule**: Template Method hook valid by design; DRY reduction optional.

**Evidence**:

```python
# repeated pattern
return "openalex_id"  # or doi/pmid/paper_id
return OpenAlexPublicationEntity  # provider-specific entity class
```

**Impact**: низкий; экономия LOC, но текущая читаемость высокая.

**Recommendation**:

```python
# optional declarative variant in base
PRIMARY_ID_FIELD: ClassVar[str]
ENTITY_CLASS: ClassVar[type[BaseEntity]]
```

Сохранить hooks как fallback для backward compatibility в миграционный период.

**Verification command**:  
`rg "def _get_primary_id_field|def _get_entity_class" src/bioetl/application/pipelines -n`

## Positive Observations (verified)

1. `BasePublicationTransformer` уже централизует общую оркестрацию трансформации (validation, fallback logging, hash, entity creation), то есть ключевой DRY-рефакторинг уже реализован.
2. `BaseTransformer` и `PipelineRunner` имеют значимый объём, но не дают автоматически признаков god object по одному только LOC; требуется анализ делегирования.

## Verification Log

```bash
git branch --all --verbose --no-abbrev
find src/bioetl/application -name '*transformer*.py' -exec wc -l {} + | sort -rn | head -30
wc -l src/bioetl/application/core/base_transformer.py src/bioetl/application/core/runner.py
grep -o "self\._[a-z_][a-z0-9_]*" src/bioetl/application/core/base_transformer.py | sort -u | wc -l
grep -o "self\._[a-z_][a-z0-9_]*" src/bioetl/application/core/runner.py | sort -u | wc -l
rg "def __init__\(" src/bioetl/application/pipelines/{openalex,crossref,semanticscholar,pubmed}/transformer.py -n
rg "def _get_primary_id_field|def _get_entity_class" src/bioetl/application/pipelines -n
rg "from bioetl\.application\.pipelines\.(openalex|crossref|semanticscholar|pubmed)\.transformer import|import bioetl\.application\.pipelines\.(openalex|crossref|semanticscholar|pubmed)\.transformer" src tests -n
uv run python -m pytest tests/architecture/test_transformer_signatures.py -q
```

## Requires Manual Review

- Повторить консолидацию после предоставления/публикации refs трех запрошенных веток.

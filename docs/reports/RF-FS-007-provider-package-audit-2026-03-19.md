# RF-FS-007 Provider Package Audit

**Дата:** 2026-03-19  
**Тема:** Аудит реальных `infrastructure/adapters/{provider}` packages после фиксации package contract  
**Связанный baseline:** [RF-FS-007-baseline-2026-03-19.md](./RF-FS-007-baseline-2026-03-19.md)

## Цель

Этот audit фиксирует не абстрактный target contract, а фактическое состояние семи
provider packages:

- `chembl`
- `crossref`
- `openalex`
- `pubchem`
- `pubmed`
- `semanticscholar`
- `uniprot`

Проверка сделана против текущего source tree и package-root exports. Задача аудита:

- подтвердить, что у каждого provider package есть понятный primary entrypoint;
- отделить intentional compatibility seams от случайного public-surface drift;
- зафиксировать реальные follow-up points вместо навязывания ложной симметрии.

## Краткий вывод

Общий contract на текущем срезе в основном соблюдается:

- у всех семи provider packages есть `__init__.py`;
- у всех есть явный primary adapter entrypoint;
- новый first-party код уже в основном импортирует adapter classes через provider
  package roots;
- retained compatibility seams для `pubmed` и `semanticscholar` выглядят
  intentional и подтверждены текущими guardrails.

Главные follow-up cases по результатам аудита:

1. `crossref`  
   `client.py` всё ещё держит расширенный compatibility surface
   (`CrossRefFetchFlow`, `CrossRefQueryBuilder`, `CrossRefResponseMapper`) сверх
   primary adapter entrypoint.

2. `uniprot`  
   baseline содержал второй публичный client surface (`UniProtIDMappingClient`) в
   package root; текущая wave проверяет и сужает этот root API до adapter-first
   shape.

## Сводная классификация

| Provider | Primary entrypoint | Root API status | Audit status | Комментарий |
| --- | --- | --- | --- | --- |
| `chembl` | `chembl/client.py` | clear | `retain` | Чистый package-root adapter export, тематический рост объясним. |
| `crossref` | `crossref/client.py` | narrowed-root / broad-client | `follow-up` | Package root сужен до adapter-first surface, но `client.py` всё ещё реэкспортирует flow/query/mapper internals для compatibility. |
| `openalex` | `openalex/client.py` | clear | `resolved-2026-03-19` | Private factory export removed from package root; helper stays local to `client.py` and dedicated tests. |
| `pubchem` | `pubchem/client.py` | clear | `retain` | Ясный entrypoint, helper/model split остаётся в infrastructure scope. |
| `pubmed` | `pubmed/client.py` | clear-with-retained-seam | `retain-documented` | Retained seam поверх legacy `pubmed_client.py` выглядит intentional. |
| `semanticscholar` | `semanticscholar/client.py` | clear-with-retained-seam | `retain-documented` | Retained seam поверх legacy `adapter.py` выглядит intentional. |
| `uniprot` | `uniprot/client.py` | narrowed-root / adjunct-submodule | `resolved-2026-03-19` | Package root сужен до adapter-first surface; adjunct ID mapping client остаётся в `uniprot.idmapping_client`. |

## Наблюдения по пакетам

### `chembl`

**Статус:** `retain`

Что видно:

- package root экспортирует `ChemblAdapter` и response/record models;
- `client.py` остаётся явным primary adapter entrypoint;
- рост пакета идёт по устойчивым темам: `models_*`, `fetch_*_mixin.py`,
  `health.py`, `metadata.py`, `entity_mapper.py`.

Оценка:

- package geography читается;
- явного misleading public surface не найдено;
- специальных follow-up действий для `RF-FS-007` не требуется.

### `crossref`

**Статус:** `follow-up`

Что видно после текущей wave:

- primary adapter entrypoint есть: `crossref/client.py`;
- package root больше не экспортирует `CrossRefFetchFlow`,
  `CrossRefQueryBuilder`, `CrossRefResponseMapper`;
- в `tests/unit/infrastructure/adapters/crossref/test_compatibility.py`
  backward compatibility по-прежнему закреплена для `client.py`.

Оценка:

- package-root surface теперь соответствует adapter-first contract;
- оставшийся широкий compatibility surface локализован в `client.py`;
- этот surface всё ещё стоит считать intentional transitional compatibility, а не
  canonical target shape для новых provider packages.

Рекомендуемый follow-up:

- не ломать текущий `client.py` surface в рамках этой минимальной wave;
- при отдельной cleanup-wave проверить, нужны ли client-level реэкспорты
  `CrossRefFetchFlow`, `CrossRefQueryBuilder`, `CrossRefResponseMapper` вне
  dedicated compatibility coverage;
- если внешняя совместимость уже не нужна, сузить root API до adapter-first shape.

### `openalex`

**Статус:** `resolved-2026-03-19`

Что было видно на baseline:

- primary adapter entrypoint есть: `openalex/client.py`;
- package root экспортирует `OpenAlexAdapter` и private helper
  `_create_openalex_adapter`;
- composition код использует `OpenAlexAdapter` напрямую, а не package-root factory;
- unit tests фабрики уже импортируют `_create_openalex_adapter` из `client.py`.

Решение текущей wave:

- package root больше не экспортирует `_create_openalex_adapter`;
- helper остаётся локальным factory helper в `openalex/client.py`;
- regression coverage закрепляет, что package root exposes adapter-only surface.

Итоговая оценка:

- исходный smell закрыт;
- дополнительных follow-up действий для `openalex` в рамках `RF-FS-007` больше не
  требуется.

### `pubchem`

**Статус:** `retain`

Что видно:

- package root экспортирует `PubChemAdapter` и record models;
- `client.py` остаётся primary entrypoint;
- helper split (`client_builders.py`, `fetch_flow.py`, `fetch_strategies.py`,
  `query_builder.py`, `response_mapper.py`) выглядит как осмысленный рост вокруг
  sync adapter.

Оценка:

- package contract соблюдён;
- отсутствие `exceptions.py` здесь не проблема, потому что этот модуль optional,
  а не mandatory.

### `pubmed`

**Статус:** `retain-documented`

Что видно:

- canonical entrypoint: `pubmed/client.py`;
- внутри него зафиксирован retained public seam поверх legacy
  `pubmed/pubmed_client.py`;
- package root экспортирует `PubMedAdapter` и `create_pubmed_adapter`;
- compatibility inventory уже явно документирует retained status этого entrypoint.

Оценка:

- текущая форма выглядит intentional;
- legacy implementation module не должен использоваться новым first-party кодом,
  но как compatibility layer он пока оправдан.

Рекомендуемый follow-up:

- оставить как есть до отдельной compatibility cleanup-wave;
- не расширять surface legacy implementation module;
- при будущей deprecation-wave отдельно пересчитать usage `create_pubmed_adapter`.

### `semanticscholar`

**Статус:** `retain-documented`

Что видно:

- canonical entrypoint: `semanticscholar/client.py`;
- он выступает retained public seam поверх legacy `semanticscholar/adapter.py`;
- package root экспортирует только `SemanticScholarAdapter` и base URL constant.

Оценка:

- retained seam выглядит чище, чем в `pubmed`, потому что root API уже узкий;
- это хороший пример controlled compatibility surface, а не package drift.

Рекомендуемый follow-up:

- оставить в текущем cycle как documented retained entrypoint;
- не возвращать прямые first-party imports на `semanticscholar/adapter.py`.

### `uniprot`

**Статус:** `resolved-2026-03-19`

Что было видно на baseline:

- primary adapter entrypoint есть: `uniprot/client.py`;
- package root экспортирует `UniProtAdapter`, модели и отдельный
  `UniProtIDMappingClient` вместе с его errors;
- `UniProtIDMappingClient` сам по себе не является `DataSourcePort`, а представляет
  отдельный adjacent client surface;
- package также содержит крупный idmapping-подкластер и отдельные private
  `_idmapping_*` implementation modules.

Решение текущей wave:

- package root больше не экспортирует `UniProtIDMappingClient` и связанные errors;
- adjunct client остаётся доступным через `bioetl.infrastructure.adapters.uniprot.idmapping_client`;
- composition code уже использовал этот более узкий import path напрямую, поэтому
  change не потребовал широкого rewiring.

Итоговая оценка:

- исходный root-surface smell закрыт;
- adjunct client остаётся intentional provider-local submodule surface, но больше
  не смешивается с package-root adapter contract.

## Итог по Definition of Done

Что подтверждено этим audit:

- существует явный adapter package contract;
- все семь текущих provider packages имеют primary entrypoint;
- packages не обязаны содержать `transformer.py` или другие application-level
  artifacts;
- явные intentional retained seams для `pubmed` и `semanticscholar` подтверждены.

Что остаётся открытым в `RF-FS-007` после этого audit:

- определить, считать ли расширенный `crossref` root API долгосрочным compatibility
  surface или кандидатом на дальнейшее сужение на уровне `client.py`.

Итоговый вывод:

`RF-FS-007` близок к завершению. На текущем срезе нет признаков массово ошибочной
структуры provider packages. Остаток задачи сводится не к широкой нормализации всех
пакетов, а к одному адресному compatibility-вопросу: `crossref/client.py`.

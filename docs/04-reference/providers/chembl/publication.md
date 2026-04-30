______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Publication

**Имя пайплайна:** `chembl_publication`
**Провайдер:** `chembl`
**Сущность:** `publication`

______________________________________________________________________

## 1. Что делает пайплайн

`chembl_publication` нормализует публикационные записи ChEMBL в unified
Silver-модель `ChemblPublication`.

Source of truth для текущего поведения:

- `configs/entities/chembl/publication.yaml`
- `src/bioetl/application/pipelines/chembl/publication_transformer.py`
- `src/bioetl/domain/schemas/chembl/publication.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`

______________________________________________________________________

## 2. Конфигурация

Текущая config-поверхность задаёт:

- `quality.entity_field_validations` для `publication_id`, `publication_type`, `publication_year`, `publication_pmid`, `publication_doi`, `title`, `citations_received`, `citations_made`
- `quality.entity_cross_field_validations`:
  - `publication_id` + `title`
  - `publication_pmid` or `publication_doi`
- `filters.extraction_params`:
  - `doc_type: PUBLICATION`
  - `year__gte: 1950`
  - `year__lte: 2050`
- `filters.silver_filters.required_fields`:
  - `publication_id`
  - `publication_type`
  - `title`
- `filters.gold_filters.required_fields`:
  - `publication_id`
  - `publication_type`
  - `title`

______________________________________________________________________

## 3. Silver surface

### 3.1. Основные обязательные поля

Current Silver contract жёстко опирается на:

| Поле               | Где закреплено                  |
| ------------------ | ------------------------------- |
| `publication_id`   | YAML required + Arrow + Pandera |
| `publication_type` | YAML required + Arrow + Pandera |
| `title`            | YAML required + Arrow + Pandera |

### 3.2. Маппинг входных полей

`PublicationTransformer` поддерживает и нормализует:

- primary id: `publication_id` или legacy `document_chembl_id`
- cross-reference поля:
  - `pubmed_id -> publication_pmid`
  - `doi -> publication_doi`
  - `pmid` и `doi` как unified aliases
- журнал и пагинацию:
  - `year -> publication_year`
  - `first_page -> page_first`
  - `last_page -> page_last`
- тип публикации:
  - `doc_type -> publication_type`
  - затем `normalize_publication_type(...)`

### 3.3. Runtime/service поля в Silver

Трансформер явно добавляет в Silver surface:

- `_lookup_method = "direct"`
- `_original_id`
- `_source = "chembl"`
- `chembl_release`
- `creation_date`

Эти поля не являются drift-артефактами: они присутствуют в Arrow/Pandera
контрактах и входят в текущую модель публикации.

### 3.4. Авторы и текстовые поля

- `title` и `abstract` проходят через `DefaultDataNormalizer`
- `authors` нормализуются в сериализованное представление
- `author_keys` вычисляются отдельно для downstream matching/join сценариев

______________________________________________________________________

## 4. Валидация

### 4.1. Arrow schema

Silver Arrow schema определяется в
`src/bioetl/infrastructure/schemas/silver_chembl_core.py` как
`CHEMBL_PUBLICATION_SCHEMA`.

### 4.2. Pandera schema

Silver Pandera schema определяется в
`src/bioetl/domain/schemas/chembl/publication.py` как
`ChemblPublicationSchema`.

Страница не фиксирует literal-формулу `entity_id`: текущая реализация использует
общий identity service/base transformer.

______________________________________________________________________

## 5. CLI

```bash
bioetl run --pipeline chembl_publication
bioetl run --pipeline chembl_publication --limit 1000
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент      | Путь                                                                 |
| -------------- | -------------------------------------------------------------------- |
| Конфигурация   | `configs/entities/chembl/publication.yaml`                           |
| Трансформер    | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |
| Arrow schema   | `src/bioetl/infrastructure/schemas/silver_chembl_core.py`            |
| Pandera schema | `src/bioetl/domain/schemas/chembl/publication.py`                    |
| Pipeline defs  | `src/bioetl/application/pipelines/chembl/_pipelines.py`              |

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_publication_v1.0.json](../../contracts/gold/chembl_publication_v1.0.json)        |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_publication_v1.0.json](../../contracts/gold/chembl_publication_v1.0.json)                              |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                          |

## API Compliance

### Rate limits & retries

Официальная ChEMBL REST Web Services documentation не публикует числовой лимит запросов. EMBL-EBI Terms of Use разрешают ограничивать или отзывать доступ, если использование мешает работе сервиса. Клиент SHOULD использовать консервативный rate limiting и экспоненциальный backoff; точный retry budget — [неуточнено].

### 429 handling policy

Явная HTTP 429 policy в доступной официальной документации ChEMBL — [неуточнено]. При признаках throttling или блокировки клиент SHOULD снижать частоту запросов и прекращать burst-нагрузку.

### Authentication model

Read-only web services документированы как открытые REST endpoints; обязательная аутентификация для чтения в официальной документации не указана.

### ToS URL

- https://www.ebi.ac.uk/about/terms-of-use

### Data license

ChEMBL data are available under the Creative Commons Attribution-ShareAlike 3.0 Unported license (CC BY-SA 3.0).

### Personal data notes

Наборы данных ChEMBL по своей природе не ориентированы на персональные данные. EMBL-EBI Privacy Notice описывает обработку служебных данных доступа и журналов безопасности; API-specific guidance по персональным данным — [неуточнено].

### Official sources

- [ChEMBL REST Web Services](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL homepage / license statement](https://www.ebi.ac.uk/chembl/)
- [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use)
- [EMBL-EBI Privacy Notice](https://www.ebi.ac.uk/about/privacy-notice)

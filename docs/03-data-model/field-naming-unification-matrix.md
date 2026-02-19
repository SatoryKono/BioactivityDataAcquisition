# Матрица унификации наименований полей (source-пайплайны)

Цель: выявить однотипные данные с разными именами между source-провайдерами и предложить канонические имена. Покрытие: только бизнес-поля. Источники: `src/bioetl/infrastructure/schemas/silver.py`, профильные docs в `docs/04-reference/pipelines/`, маппинги публикаций `src/bioetl/domain/mapping/publication-fields.py`, `docs/03-data-model/rf-naming-unification-plan.md`.

Обозначения классов расхождений:
- `синоним` — разное имя, одинаковая семантика.
- `префикс/контекст` — различие только в контекстном префиксе.
- `legacy` — устаревшее имя из прошлого API.
- `типовой конфликт` — различие имён + разный формат/тип.

## Идентификаторы публикаций
| Канонический концепт | Провайдер → поле | Класс расхождения | Комментарий |
|---|---|---|---|
| publication-doi | chembl:`doi`; crossref:`doi`; openalex:`doi`; pubmed:`doi`; semanticscholar:`doi` | префикс/контекст | Совпадает по имени, разный формат (строка, lower). |
| publication-pmid | chembl:`pmid`; pubmed:`pmid`; openalex:`pmid`; semanticscholar:`pmid`; crossref:`pmid` (null) | синоним | Единый snake-case, тип string. |
| publication-pmc-id | chembl:`pmc-id`; pubmed:`pmc-id`; crossref/openalex/semanticscholar:`pmc-id` | синоним | Единый snake-case, string. |
| provider-primary-id | chembl:`document-chembl-id`; openalex:`openalex-id`; semanticscholar:`paper-id`; pubmed:`pmid`; crossref:`doi` | типовой конфликт | Разные ключи по провайдерам; нужен alias-реестр. |

## Метрики цитирования и ссылки
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| citations-received | chembl:`citations-received`; crossref:`citations-received` (is-referenced-by-count); openalex:`citations-received`; semanticscholar:`citations-received`; pubmed: n/a | синоним | Одинаковое имя, одна семантика. |
| citations-made | chembl:`citations-made`; crossref:`citations-made` (references-count); openalex:`citations-made`; semanticscholar:`citations-made`; pubmed:`citations-made` | синоним | Одинаковое имя. |

## Библиография публикаций
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| publication-year | chembl:`publication-year`; pubmed:`publication-year`; crossref:`publication-year`; openalex:`publication-year`; semanticscholar:`publication-year`; chembl-activity:`document-year` | префикс/контекст | Activity legacy `document-year` → переименовать в `publication-year` (breaking). |
| journal-name | chembl:`journal`; pubmed:`journal`; crossref:`journal`; openalex:`journal`; semanticscholar:`journal`; chembl-activity:`document-journal` | префикс/контекст | Activity legacy `document-journal` → переименовать в `journal` (breaking). |
| page-first / page-last | chembl:`page-first`/`page-last`; pubmed:`page-first`/`page-last`; crossref:`page-first`/`page-last`; openalex:`page-first`/`page-last`; semanticscholar:`page-first`/`page-last` | синоним | Формат строка, диапазон в отдельных полях. |
| publication-type | chembl:`publication-type`; pubmed:`publication-type`; crossref:`publication-type`; openalex:`publication-type`; semanticscholar:`publication-type` | синоним | Единый unified тип. |

## Организм / таксономия
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| taxonomy-id | chembl-target:`taxonomy-id`; chembl-target-component:`taxonomy-id`; chembl-assay:`assay-taxonomy-id`; chembl-assay:`variant-taxonomy-id`; chembl-activity:`target-taxonomy-id`; uniprot-idmapping:`taxonomy-id`; uniprot-protein:`organism-id` | типовой конфликт | Разные имена/типы (int/float/string). Нужна нормализация в единый `taxonomy-id` (float, nullable int pattern). |
| organism-name | chembl-assay:`assay-organism`; chembl-target:`organism`; chembl-target-component:`organism`; uniprot-idmapping:`organism-scientific`/`organism-common`; uniprot-protein: отсутствует строковый organism, только ID | префикс/контекст | Единый префикс `organism-*` и int ID. |

## Молекулярные идентификаторы и дескрипторы
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| molecule-id | chembl-molecule:`molecule-chembl-id`; pubchem-compound:`cid`; chembl-activity:`molecule-chembl-id`; chembl-compound-record:`molecule-chembl-id` | типовой конфликт | Разные нотации; требуется alias-колонка `molecule-id` + `provider-molecule-id`. |
| inchi-key | chembl-molecule:`inchikey`; pubchem-compound:`inchikey`; chembl-activity:`canonical-smiles` (структурный идентификатор, не InChIKey) | синоним | Имя совпадает, формат стандартный. |
| molecular-weight | chembl-molecule:`property-full-mwt`; pubchem-compound:`molecular-weight` | типовой конфликт | Нужно привести к `molecular-weight` (float) с alias. |
| logp | chembl-molecule:`property-alogp`; pubchem-compound:`xlogp` | типовой конфликт | Канонизировать как `logp` с указанием метода (AlogP/XlogP). |
| psa | chembl-molecule:`property-psa`; pubchem-compound:`tpsa` | префикс/контекст | Выбрать `polar-surface-area` с alias. |
| rotatable-bond-count | chembl-molecule:`property-rtb`; pubchem-compound:`rotatable-bonds` (нет в схеме) | legacy | Канон: `rotatable-bond-count`; в PubChem текущей схеме поля нет. |

## Названия и описания
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| pref-name | chembl-molecule:`pref-name`; chembl-target:`pref-name`; chembl-activity:`molecule-pref-name`/`target-pref-name`; chembl-tissue:`pref-name`; chembl-protein-class:`pref-name`; uniprot-protein:`protein-name` | префикс/контекст | Единый `*-pref-name` по сущности; для белков — `protein-name`. |
| description | chembl-assay:`description`; chembl-target-component:`description`; chembl-activity:`assay-description`; chembl-molecule: нет отдельного description | префикс/контекст | Уточнить, что `assay-description` → `description` в контексте assay. |

## Статусы open access и типы публикаций
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| is-oa | chembl-publication:`is-oa`; openalex:`is-oa`; semanticscholar:`is-oa`; crossref:`is-oa`(нет); pubmed:`is-oa`(нет) | типовой конфликт | Поле есть не у всех; канонизировать `is-oa` bool, отсутствие → null. |
| oa-status | openalex:`oa-status`; semanticscholar:`oa-status`; crossref/pubmed/chembl: нет | типовой конфликт | Ввести optional `oa-status` c словарём значений. |

## Связи Activity ↔ Publication/Assay/Target
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| publication-id | chembl-activity:`document-chembl-id`; chembl-assay:`document-chembl-id` | префикс/контекст | Использовать `publication-id` (alias на provider PK). |
| assay-id | chembl-activity:`assay-chembl-id`; chembl-assay:`assay-chembl-id`; chembl-assay-parameters:`assay-chembl-id` | синоним | Единое имя `assay-id`. |
| target-id | chembl-activity:`target-chembl-id`; chembl-assay:`target-chembl-id`; chembl-target:`target-chembl-id`; uniprot-idmapping:`target-chembl-id` | синоним | Единое имя `target-id`. |

## Ключевые выводы
- Большинство публикационных полей уже унифицированы; основные расхождения — PK и контекстные префиксы (`document-*` vs `publication-*`).
- В молекулярных дескрипторах различаются имена и метод расчёта (ALogP/XlogP, full-mwt/molecular-weight, PSA/tPSA).
- Таксономические поля разделены по сущностям (`target-taxonomy-id`, `assay-taxonomy-id`, `taxonomy-id`, `organism-id`) и имеют разные типы; требуется единый `taxonomy-id:int64` + контекстное имя `taxonomy-scope` при необходимости.
- Связи между сущностями используют provider-специфичные PK; необходим слой алиасов + единые поля (`publication-id`, `assay-id`, `target-id`, `molecule-id`).

## Целевая номенклатура и правила
- Базовый стиль: `snake-case`, суффиксы `*-id`, `*-name`, `*-count`, `is-*`, `*-year`, `*-date`.
- Идентификаторы публикаций:
  - PK провайдера в поле `provider-publication-id`; алиасы: `document-chembl-id`, `paper-id`, `openalex-id`, `pmid`, `doi` остаются как provider-columns.
  - Единые поля связей: `publication-id` (строковый, заполняется PK провайдера), `publication-doi`, `publication-pmid`, `publication-pmc-id`.
- Библиография: `journal`, `publication-year`, `page-first`, `page-last`, `publication-type`, `publication-type-unified`, `publication-class`, `publication-subclass`.
- Метрики: `citations-received`, `citations-made` (int64, nullable).
- Open Access: `is-oa` (bool, nullable), `oa-status` (string словарь).
- Таксономия: единое `taxonomy-id:int64`; при необходимости контекст `taxonomy-scope` (`target`, `assay`, `variant`, `cell-source`).
- Молекулярные идентификаторы:
  - `molecule-id` — канонический ключ пайплайна; алиасы `molecule-chembl-id` и `cid`.
  - `inchi-key`, `canonical-smiles`, `standard-inchi`.
- Молекулярные свойства:
  - `molecular-weight` (float64) с алиасами `property-full-mwt`.
  - `logp` с параметром метода (`alogp`/`xlogp`) в отдельном поле `logp-method`.
  - `polar-surface-area` (alias `property-psa` / `tpsa`).
- Названия/описания:
  - `pref-name` для сущностей; контекстный префикс только при многократном присутствии в записи (`molecule-pref-name`, `target-pref-name` внутри activity).
  - `description` — основное описание сущности; специализированные варианты переименовывать в `*-description` только при наличии нескольких описаний.


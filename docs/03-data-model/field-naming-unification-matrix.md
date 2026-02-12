# Матрица унификации наименований полей (source-пайплайны)

Цель: выявить однотипные данные с разными именами между source-провайдерами и предложить канонические имена. Покрытие: только бизнес-поля. Источники: `src/bioetl/infrastructure/schemas/silver.py`, профильные docs в `docs/04-reference/pipelines/`, маппинги публикаций `src/bioetl/domain/mapping/publication_fields.py`, `docs/03-data-model/rf-naming-unification-plan.md`.

Обозначения классов расхождений:
- `синоним` — разное имя, одинаковая семантика.
- `префикс/контекст` — различие только в контекстном префиксе.
- `legacy` — устаревшее имя из прошлого API.
- `типовой конфликт` — различие имён + разный формат/тип.

## Идентификаторы публикаций
| Канонический концепт | Провайдер → поле | Класс расхождения | Комментарий |
|---|---|---|---|
| publication_doi | chembl:`doi`; crossref:`doi`; openalex:`doi`; pubmed:`doi`; semanticscholar:`doi` | префикс/контекст | Совпадает по имени, разный формат (строка, lower). |
| publication_pmid | chembl:`pmid`; pubmed:`pmid`; openalex:`pmid`; semanticscholar:`pmid`; crossref:`pmid` (null) | синоним | Единый snake_case, тип string. |
| publication_pmc_id | chembl:`pmc_id`; pubmed:`pmc_id`; crossref/openalex/semanticscholar:`pmc_id` | синоним | Единый snake_case, string. |
| provider_primary_id | chembl:`document_chembl_id`; openalex:`openalex_id`; semanticscholar:`paper_id`; pubmed:`pmid`; crossref:`doi` | типовой конфликт | Разные ключи по провайдерам; нужен alias-реестр. |

## Метрики цитирования и ссылки
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| citations_received | chembl:`citations_received`; crossref:`citations_received` (is-referenced-by-count); openalex:`citations_received`; semanticscholar:`citations_received`; pubmed: n/a | синоним | Одинаковое имя, одна семантика. |
| citations_made | chembl:`citations_made`; crossref:`citations_made` (references-count); openalex:`citations_made`; semanticscholar:`citations_made`; pubmed:`citations_made` | синоним | Одинаковое имя. |

## Библиография публикаций
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| publication_year | chembl:`publication_year`; pubmed:`publication_year`; crossref:`publication_year`; openalex:`publication_year`; semanticscholar:`publication_year`; chembl_activity:`document_year` | префикс/контекст | Activity legacy `document_year` → переименовать в `publication_year` (breaking). |
| journal_name | chembl:`journal`; pubmed:`journal`; crossref:`journal`; openalex:`journal`; semanticscholar:`journal`; chembl_activity:`document_journal` | префикс/контекст | Activity legacy `document_journal` → переименовать в `journal` (breaking). |
| page_first / page_last | chembl:`page_first`/`page_last`; pubmed:`page_first`/`page_last`; crossref:`page_first`/`page_last`; openalex:`page_first`/`page_last`; semanticscholar:`page_first`/`page_last` | синоним | Формат строка, диапазон в отдельных полях. |
| publication_type | chembl:`publication_type`; pubmed:`publication_type`; crossref:`publication_type`; openalex:`publication_type`; semanticscholar:`publication_type` | синоним | Единый unified тип. |

## Организм / таксономия
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| taxonomy_id | chembl_target:`taxonomy_id`; chembl_target_component:`taxonomy_id`; chembl_assay:`assay_taxonomy_id`; chembl_assay:`variant_taxonomy_id`; chembl_activity:`target_taxonomy_id`; uniprot_idmapping:`taxonomy_id`; uniprot_protein:`organism_id` | типовой конфликт | Разные имена/типы (int/float/string). Нужна нормализация в единый `taxonomy_id` (float, nullable int pattern). |
| organism_name | chembl_assay:`assay_organism`; chembl_target:`organism`; chembl_target_component:`organism`; uniprot_idmapping:`organism_scientific`/`organism_common`; uniprot_protein: отсутствует строковый organism, только ID | префикс/контекст | Единый префикс `organism_*` и int ID. |

## Молекулярные идентификаторы и дескрипторы
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| molecule_id | chembl_molecule:`molecule_chembl_id`; pubchem_compound:`cid`; chembl_activity:`molecule_chembl_id`; chembl_compound_record:`molecule_chembl_id` | типовой конфликт | Разные нотации; требуется alias-колонка `molecule_id` + `provider_molecule_id`. |
| inchi_key | chembl_molecule:`inchikey`; pubchem_compound:`inchikey`; chembl_activity:`canonical_smiles` (структурный идентификатор, не InChIKey) | синоним | Имя совпадает, формат стандартный. |
| molecular_weight | chembl_molecule:`property_full_mwt`; pubchem_compound:`molecular_weight` | типовой конфликт | Нужно привести к `molecular_weight` (float) с alias. |
| logp | chembl_molecule:`property_alogp`; pubchem_compound:`xlogp` | типовой конфликт | Канонизировать как `logp` с указанием метода (AlogP/XlogP). |
| psa | chembl_molecule:`property_psa`; pubchem_compound:`tpsa` | префикс/контекст | Выбрать `polar_surface_area` с alias. |
| rotatable_bond_count | chembl_molecule:`property_rtb`; pubchem_compound:`rotatable_bonds` (нет в схеме) | legacy | Канон: `rotatable_bond_count`; в PubChem текущей схеме поля нет. |

## Названия и описания
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| pref_name | chembl_molecule:`pref_name`; chembl_target:`pref_name`; chembl_activity:`molecule_pref_name`/`target_pref_name`; chembl_tissue:`pref_name`; chembl_protein_class:`pref_name`; uniprot_protein:`protein_name` | префикс/контекст | Единый `*_pref_name` по сущности; для белков — `protein_name`. |
| description | chembl_assay:`description`; chembl_target_component:`description`; chembl_activity:`assay_description`; chembl_molecule: нет отдельного description | префикс/контекст | Уточнить, что `assay_description` → `description` в контексте assay. |

## Статусы open access и типы публикаций
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| is_oa | chembl_publication:`is_oa`; openalex:`is_oa`; semanticscholar:`is_oa`; crossref:`is_oa`(нет); pubmed:`is_oa`(нет) | типовой конфликт | Поле есть не у всех; канонизировать `is_oa` bool, отсутствие → null. |
| oa_status | openalex:`oa_status`; semanticscholar:`oa_status`; crossref/pubmed/chembl: нет | типовой конфликт | Ввести optional `oa_status` c словарём значений. |

## Связи Activity ↔ Publication/Assay/Target
| Канонический концепт | Провайдер → поле | Класс | Комментарий |
|---|---|---|---|
| publication_id | chembl_activity:`document_chembl_id`; chembl_assay:`document_chembl_id` | префикс/контекст | Использовать `publication_id` (alias на provider PK). |
| assay_id | chembl_activity:`assay_chembl_id`; chembl_assay:`assay_chembl_id`; chembl_assay_parameters:`assay_chembl_id` | синоним | Единое имя `assay_id`. |
| target_id | chembl_activity:`target_chembl_id`; chembl_assay:`target_chembl_id`; chembl_target:`target_chembl_id`; uniprot_idmapping:`target_chembl_id` | синоним | Единое имя `target_id`. |

## Ключевые выводы
- Большинство публикационных полей уже унифицированы; основные расхождения — PK и контекстные префиксы (`document_*` vs `publication_*`).
- В молекулярных дескрипторах различаются имена и метод расчёта (ALogP/XlogP, full_mwt/molecular_weight, PSA/tPSA).
- Таксономические поля разделены по сущностям (`target_taxonomy_id`, `assay_taxonomy_id`, `taxonomy_id`, `organism_id`) и имеют разные типы; требуется единый `taxonomy_id:int64` + контекстное имя `taxonomy_scope` при необходимости.
- Связи между сущностями используют provider-специфичные PK; необходим слой алиасов + единые поля (`publication_id`, `assay_id`, `target_id`, `molecule_id`).

## Целевая номенклатура и правила
- Базовый стиль: `snake_case`, суффиксы `*_id`, `*_name`, `*_count`, `is_*`, `*_year`, `*_date`.
- Идентификаторы публикаций:
  - PK провайдера в поле `provider_publication_id`; алиасы: `document_chembl_id`, `paper_id`, `openalex_id`, `pmid`, `doi` остаются как provider_columns.
  - Единые поля связей: `publication_id` (строковый, заполняется PK провайдера), `publication_doi`, `publication_pmid`, `publication_pmc_id`.
- Библиография: `journal`, `publication_year`, `page_first`, `page_last`, `publication_type`, `publication_type_unified`, `publication_class`, `publication_subclass`.
- Метрики: `citations_received`, `citations_made` (int64, nullable).
- Open Access: `is_oa` (bool, nullable), `oa_status` (string словарь).
- Таксономия: единое `taxonomy_id:int64`; при необходимости контекст `taxonomy_scope` (`target`, `assay`, `variant`, `cell_source`).
- Молекулярные идентификаторы:
  - `molecule_id` — канонический ключ пайплайна; алиасы `molecule_chembl_id` и `cid`.
  - `inchi_key`, `canonical_smiles`, `standard_inchi`.
- Молекулярные свойства:
  - `molecular_weight` (float64) с алиасами `property_full_mwt`.
  - `logp` с параметром метода (`alogp`/`xlogp`) в отдельном поле `logp_method`.
  - `polar_surface_area` (alias `property_psa` / `tpsa`).
- Названия/описания:
  - `pref_name` для сущностей; контекстный префикс только при многократном присутствии в записи (`molecule_pref_name`, `target_pref_name` внутри activity).
  - `description` — основное описание сущности; специализированные варианты переименовывать в `*_description` только при наличии нескольких описаний.


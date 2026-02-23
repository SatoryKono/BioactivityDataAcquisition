# Каталог бизнес-полей source-пайплайнов

Область: только source-пайплайны (ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar). Служебные поля (`entity-id`, `content-hash`, `-run-id`, `-run-type`, `-source-batch-id`, `-source`, `-ingestion-ts`, `-index`, `-dq-error`, `-dq-warn`) опущены и описаны кратко в конце. Типы взяты из PyArrow-схем `src/bioetl/infrastructure/schemas/silver.py`, семантика — из комментариев схем и профильных docs.

Формат таблиц: `поле | тип | что хранится / правило`.

## ChEMBL

### chembl-publication
| Поле | Тип | Описание |
|---|---|---|
| authors | string | JSON-массив авторов (строки) |
| title | string | Заголовок публикации |
| journal | string | Название журнала |
| publication-year | int64 | Год публикации |
| volume | string | Том издания |
| issue | string | Номер выпуска |
| page-first | string | Первая страница (нормализовано) |
| page-last | string | Последняя страница (нормализовано) |
| document-chembl-id | string | PK документа ChEMBL |
| doi | string | DOI без префикса https://doi.org/ |
| pmc-id | string | PubMed Central ID |
| pmid | string | PubMed ID (строкой) |
| abstract | string | Аннотация |
| affiliation-list | string | JSON-массив аффилиаций (для ChEMBL — пусто) |
| author-orcids | string | JSON-массив ORCID (для ChEMBL — пусто) |
| publication-type | string | Тип из ChEMBL, приведённый к unified |
| publication-type-unified | string | Тип публикации L3 (Journal Article и т.п.) |
| publication-subclass | string | Подкласс L2 |
| publication-class | string | Класс L1 (`EXP`/`REV`/`PEER`) |
| publication-date | string | Дата публикации (YYYY-MM-DD, обычно null для ChEMBL) |
| language | string | Язык (обычно null) |
| is-oa | bool | Флаг open access (обычно null) |
| src-id | int64 | Идентификатор источника записи |
| citations-received | int64 | Кол-во входящих цитат (unified) |
| citations-made | int64 | Кол-во исходящих ссылок (unified) |
| chembl-release | string | Версия ChEMBL (CHEMBL-XX) |
| creation-date | string | Дата создания записи (YYYY-MM-DD) |

### chembl_activity
| Поле | Тип | Описание |
|---|---|---|
| action-type-action-type | string | Тип действия (ChEMBL action-type) |
| action-type-description | string | Описание action-type |
| action-type-parent-type | string | Родительский тип action-type |
| activity-comment | string | Комментарий к измерению |
| activity-id | string | PK активности |
| activity-properties | string | JSON со свойствами активности |
| assay-chembl-id | string | FK на анализ |
| assay-description | string | Описание анализа |
| assay-type | string | Тип анализа |
| assay-variant-accession | string | Accession варианта белка |
| assay-variant-mutation | string | Мутация варианта |
| bao-endpoint | string | BAO endpoint |
| bao-format | string | BAO формат |
| bao-label | string | BAO метка |
| canonical-smiles | string | Канонический SMILES лиганда |
| data-validity-comment | string | Комментарий валидности данных |
| data-validity-description | string | Описание валидности |
| document-chembl-id | string | FK на публикацию |
| document-journal | string | Журнал из документа |
| document-year | int64 | Год публикации документа |
| ligand-efficiency-bei | float64 | Binding Efficiency Index |
| ligand-efficiency-le | float64 | Ligand Efficiency |
| ligand-efficiency-lle | float64 | Lipophilic Ligand Efficiency |
| ligand-efficiency-sei | float64 | Surface Efficiency Index |
| manual-curation-flag | float64 | Флаг ручной проверки (nullable int) |
| molecule-chembl-id | string | FK на молекулу |
| molecule-pref-name | string | Предпочтительное имя молекулы |
| original-activity-id | float64 | Исходный ID активности |
| parent-molecule-chembl-id | string | Родительская молекула |
| pchembl-value | float64 | pChEMBL значение |
| potential-duplicate | int64 | Флаг потенциального дубликата |
| qudt-units | string | QUDT единицы |
| record-id | int64 | ID записи активности |
| relation | string | Отношение (`=`, `>`, `<`) |
| src-id | int64 | Источник данных |
| standard-flag | int64 | Флаг стандартизации |
| standard-relation | string | Стандартизированное отношение |
| standard-text-value | string | Текстовое значение (стандартиз.) |
| standard-type | string | Стандартизированный тип измерения |
| standard-units | string | Стандартизированные единицы |
| standard-upper-value | float64 | Верхняя граница значения |
| standard-value | float64 | Стандартизированное числовое значение |
| target-chembl-id | string | FK на мишень |
| target-organism | string | Организм мишени |
| target-pref-name | string | Предпочтительное имя мишени |
| target-taxonomy-id | float64 | NCBI Taxonomy ID мишени (nullable int, унифицированное имя) |
| text-value | string | Исходное текстовое значение |
| toid | float64 | Target Ontology ID (nullable int) |
| type | string | Тип активности |
| units | string | Единицы (сырье) |
| uo-units | string | Единицы из Unit Ontology |
| upper-value | float64 | Верхняя граница (сырье) |
| value | float64 | Значение (сырье) |

### chembl-assay
| Поле | Тип | Описание |
|---|---|---|
| aidx | string | Внутренний ID анализа |
| assay-category | string | Категория анализа |
| assay-cell-type | string | Тип клетки |
| assay-chembl-id | string | PK анализа |
| assay-classifications | string | JSON классификаций |
| assay-group | string | Группа анализа |
| assay-organism | string | Организм |
| assay-parameters | string | JSON параметров |
| assay-pref-name | string | Предпочтительное имя |
| assay-strain | string | Штамм |
| assay-subcellular-fraction | string | Субклеточная фракция |
| assay-taxonomy-id | float64 | Таксономия (nullable int) |
| assay-test-type | string | Тип теста |
| assay-tissue | string | Ткань |
| assay-type | string | Тип (из API) |
| assay-type-description | string | Описание типа |
| bao-format | string | BAO формат |
| bao-label | string | BAO метка |
| cell-chembl-id | string | FK на клеточную линию |
| confidence-description | string | Описание confidence-score |
| confidence-score | int64 | Оценка уверенности |
| description | string | Описание анализа |
| document-chembl-id | string | FK на публикацию |
| relationship-description | string | Описание отношения к мишени |
| relationship-type | string | Тип отношения |
| score | float64 | Счёт анализа |
| src-assay-id | string | Исходный ID анализа |
| src-id | int64 | Источник данных |
| target-chembl-id | string | FK на мишень |
| tissue-chembl-id | string | FK на ткань |
| variant-accession | string | Accession варианта |
| variant-isoform | string | Изоформа |
| variant-mutation | string | Мутация |
| variant-organism | string | Организм варианта |
| variant-sequence | string | Последовательность |
| variant-sequence-json | string | JSON исходной последовательности |
| variant-taxonomy-id | float64 | Таксономия варианта (nullable int) |

### chembl-assay-parameters
| Поле | Тип | Описание |
|---|---|---|
| assay-chembl-id | string | FK на анализ |
| assay-param-id | int64 | PK параметра |
| comments | string | Комментарий |
| relation | string | Исходное отношение |
| standard-relation | string | Стандартизированное отношение |
| standard-text-value | string | Текстовое значение (стандартиз.) |
| standard-type | string | Стандартизированный тип параметра |
| standard-units | string | Стандартизированные единицы |
| standard-value | float64 | Стандартизированное значение |
| text-value | string | Исходное текстовое значение |
| type | string | Тип параметра |
| units | string | Единицы измерения |
| value | float64 | Числовое значение |

### chembl-target
| Поле | Тип | Описание |
|---|---|---|
| component-accessions | list<string> | Accession компонентов |
| component-descriptions | list<string> | Описания компонентов |
| component-id | float64 | ID компонента (nullable) |
| component-ids | list<int64> | Список ID компонентов |
| component-relationships | list<string> | Связи компонентов |
| component-types | list<string> | Типы компонентов |
| cross-references | string | JSON кросс-референсов |
| downgraded | bool | Флаг понижения статуса |
| organism | string | Организм |
| pipeline-stages | string | JSON стадий пайплайна |
| pref-name | string | Предпочтительное имя мишени |
| species-group-flag | bool | Флаг групповой мишени |
| target-chembl-id | string | PK мишени |
| target-component-synonyms | string | Синонимы компонентов (JSON) |
| target-components | string | Компоненты (JSON) |
| target-type | string | Тип мишени |
| taxonomy-id | float64 | NCBI Taxonomy ID (nullable) |

### chembl-target-component
| Поле | Тип | Описание |
|---|---|---|
| accession | string | UniProt accession |
| component-id | int64 | PK компонента |
| component-type | string | Тип компонента |
| description | string | Описание |
| organism | string | Организм |
| protein-classification-id | int64 | Основной класс белка |
| protein-classification-ids | list<int64> | Все классы белка |
| protein-classifications | string | Исходный JSON классификаций |
| target-component-synonyms | string | Синонимы (JSON) |
| target-component-xrefs | string | Кросс-референсы (JSON) |
| taxonomy-id | int64 | NCBI Taxonomy ID |

### chembl-cell-line
| Поле | Тип | Описание |
|---|---|---|
| cell-chembl-id | string | PK клеточной линии |
| cell-description | string | Описание |
| cell-name | string | Имя линии |
| cell-source-organism | string | Организм источника |
| cell-source-taxonomy-id | int64 | Таксономия источника |
| cell-source-tissue | string | Ткань источника |
| cellosaurus-id | string | Cellosaurus ID |
| cl-lincs-id | string | LINCS ID |
| efo-id | string | EFO ID |

### chembl-tissue
| Поле | Тип | Описание |
|---|---|---|
| bto-id | string | BRENDA Tissue Ontology ID |
| caloha-id | string | CALIPHO ID |
| efo-id | string | EFO ID |
| pref-name | string | Предпочтительное имя ткани |
| tissue-chembl-id | string | PK ткани |
| uberon-id | string | Uberon ID |

### chembl-subcellular-fraction
| Поле | Тип | Описание |
|---|---|---|
| assay-count | int64 | Кол-во анализов с этой фракцией |
| example-assay-chembl-id | string | Пример ChEMBL assay |
| subcellular-fraction | string | Название фракции (PK) |

### chembl-document-term
| Поле | Тип | Описание |
|---|---|---|
| document-chembl-id | string | PK публикации |
| mesh-id | string | MeSH ID |
| qualifier | string | Квалификатор MeSH |
| term | string | Терм MeSH |
| term-type | string | Тип терма |

### chembl-molecule
| Поле | Тип | Описание |
|---|---|---|
| atc-classifications | string | ATC классификации (JSON) |
| availability-type | float64 | Тип доступности (nullable int) |
| black-box-warning | int64 | BBW флаг |
| canonical-smiles | string | Канонический SMILES |
| chirality | int64 | Хиральность |
| cross-references | string | JSON кросс-референсов |
| dosed-ingredient | int64 | Флаг дозируемого ингредиента |
| first-approval | float64 | Год первого одобрения (nullable int) |
| first-in-class | int64 | Флаг первого в классе |
| helm-notation | string | HELM нотация |
| hierarchy-active-chembl-id | string | Активный ID в иерархии |
| hierarchy-child-chembl-id | string | Дочерний ID |
| hierarchy-parent-chembl-id | string | Родительский ID |
| inchikey | string | InChIKey |
| inorganic-flag | int64 | Флаг неорганичности |
| max-phase | int64 | Максимальная фаза клинических испытаний |
| molecule-chembl-id | string | PK молекулы |
| molecule-hierarchy | string | JSON иерархии |
| molecule-properties | string | JSON свойств |
| molecule-species | string | Вид |
| molecule-structures | string | JSON структур |
| molecule-synonyms | string | Синонимы (JSON) |
| molecule-type | string | Тип молекулы |
| natural-product | int64 | Флаг натурального происхождения |
| oral | bool | Пероральность |
| parenteral | bool | Парентеральность |
| polymer-flag | int64 | Полимер флаг |
| pref-name | string | Предпочтительное имя |
| prodrug | int64 | Флаг пролекарства |
| property-alogp | float64 | ALogP |
| property-aromatic-rings | int64 | Кол-во ароматических колец |
| property-full-molformula | string | Полная формула |
| property-full-mwt | float64 | Полная мол. масса |
| property-hba | int64 | Кол-во акцепторов H |
| property-hbd | int64 | Кол-во доноров H |
| property-heavy-atoms | int64 | Кол-во тяжёлых атомов |
| property-mw-freebase | float64 | Мол. масса freebase |
| property-psa | float64 | Полярная площадь |
| property-qed-weighted | float64 | QED (взвеш.) |
| property-ro3-pass | string | Соответствие RO3 |
| property-ro5-violations | int64 | Нарушения RO5 |
| property-rtb | int64 | Кол-во вращаемых связей |
| standard-inchi | string | Standard InChI |
| structure-type | string | Тип структуры |
| therapeutic-flag | bool | Флаг лекарственного средства |
| topical | bool | Наружное применение |
| usan-stem | string | USAN стем |
| usan-stem-definition | string | Описание стема |
| usan-substem | string | Substem |
| usan-year | float64 | Год присвоения USAN (nullable int) |
| withdrawn-flag | bool | Флаг отзыва |

### chembl-compound-record
| Поле | Тип | Описание |
|---|---|---|
| compound-key | string | Ключ соединения из документа |
| compound-name | string | Имя соединения из документа |
| document-chembl-id | string | FK на публикацию |
| molecule-chembl-id | string | FK на молекулу |
| record-id | int64 | ID записи |
| src-compound-id | string | ID соединения в источнике |
| src-id | int64 | Источник данных |

### chembl-document-similarity
| Поле | Тип | Описание |
|---|---|---|
| avg-tani | float64 | Средний Tanimoto |
| doc-1 | int64 | Doc ID 1 |
| doc-2 | int64 | Doc ID 2 |
| max-tani | float64 | Максимальный Tanimoto |
| mol-tani | float64 | Tanimoto по молекулам |
| pubmed-id1 | string | PubMed ID 1 |
| pubmed-id2 | string | PubMed ID 2 |
| sim-id | int64 | ID похожести |
| tid-tani | float64 | Tanimoto по target |

## PubChem

### pubchem-compound
| Поле | Тип | Описание |
|---|---|---|
| canonical-smiles | string | Канонический SMILES |
| cid | string | PubChem CID (PK, строкой) |
| complexity | float64 | Сложность |
| conformer-count-3d | float64 | Кол-во конформеров 3D |
| conformer-rmsd-3d | float64 | RMSD конформеров |
| effective-rotor-count-3d | float64 | Эффективные ротаторы |
| exact-mass | float64 | Точная масса |
| feature-acceptor-count-3d | float64 | 3D акцепторы |
| feature-anion-count-3d | float64 | 3D анионы |
| feature-cation-count-3d | float64 | 3D катионы |
| feature-count-3d | float64 | Всего 3D фичей |
| feature-donor-count-3d | float64 | 3D доноры |
| feature-hydrophobe-count-3d | float64 | 3D гидрофобы |
| feature-ring-count-3d | float64 | 3D кольца |
| inchi | string | InChI |
| inchikey | string | InChIKey |
| isomeric-smiles | string | Изомерный SMILES |
| iupac-name | string | IUPAC имя |
| molecular-formula | string | Молекулярная формула |
| molecular-weight | float64 | Молекулярная масса |
| monoisotopic-mass | float64 | Моноизотопная масса |
| tpsa | float64 | Полярная площадь |
| x-steric-quadrupole-3d | float64 | Стерический квадруполь X |
| xlogp | float64 | XlogP |
| y-steric-quadrupole-3d | float64 | Стерический квадруполь Y |
| z-steric-quadrupole-3d | float64 | Стерический квадруполь Z |

## UniProt

### uniprot-protein
| Поле | Тип | Описание |
|---|---|---|
| accession | string | UniProt accession (PK) |
| acetylation | string | Места ацетилирования (PTM) |
| active-sites | string | Активные сайты (JSON) |
| activity-regulation | string | Регуляция активности |
| annotation-score | int64 | Качество аннотации (1–5) |
| binding-sites | string | Узлы связывания (JSON) |
| catalytic-activity | string | Каталитическая активность |
| cellular-component | string | GO: клеточный компонент |
| chembl-ids | string | Кросс-референсы ChEMBL target (JSON) |
| disease-involvement | string | Заболевания |
| disulfide-bond | string | Дисульфидные связи |
| domains | string | Домены (JSON) |
| drugbank-ids | string | DrugBank IDs (JSON) |
| entry-name | string | UniProt entry name |
| features-json | string | Полный JSON фичей |
| function-comment | string | Комментарий функции |
| gene-names | list<string> | Синонимы генов |
| genus | string | Род (таксономия) |
| glycosylation | string | Гликозилирование |
| go-terms | string | GO аннотации (JSON) |
| interpro-xrefs | string | InterPro IDs (JSON) |
| intramembrane | string | Внутримембранные области |
| isoform-ids | string | ID изоформ |
| isoform-names | string | Имена изоформ |
| isoform-synonyms | string | Синонимы изоформ |
| lipidation | string | Липидация |
| modified-residue | string | Модифицированные остатки |
| molecular-function | string | GO: мол. функция |
| organism-id | int64 | NCBI Taxonomy ID |
| pathway | string | Пути (Reactome/KEGG) |
| pdb-xrefs | string | PDB ID (JSON) |
| pfam-xrefs | string | Pfam ID (JSON) |
| phosphorylation | string | Фосфорилирование |
| phylum | string | Тип (таксономия) |
| propeptide | string | Пропептиды |
| protein-existence | string | Уровень доказательств |
| protein-name | string | Реком. имя белка |
| reaction-ec-numbers | string | EC номера реакций |
| reactions | string | Описания реакций |
| reactome-xrefs | string | Reactome IDs (JSON) |
| reviewed | bool | Swiss-Prot (true) / TrEMBL (false) |
| sequence-length | int64 | Длина последовательности |
| signal-peptide | string | Сигнальный пептид |
| similarity-comment | string | Комм. схожести |
| subcellular-location | string | Локализация |
| superkingdom | string | Надцарство |
| tissue-specificity | string | Тканевая специфичность |
| topology | string | Топология |
| transmembrane | string | Трансмембранные области |
| ubiquitination | string | Убиквитинирование |

### uniprot-idmapping
| Поле | Тип | Описание |
|---|---|---|
| all-mappings | string | JSON списка маппингов |
| annotation-score | int64 | Оценка качества (1–5) |
| gene-primary | string | Основное имя гена |
| mapping-status | string | Статус (`found`/`not-found`/`error`/`multiple`) |
| organism-common | string | Обычное название организма |
| organism-scientific | string | Научное название |
| protein-name | string | Имя белка |
| reviewed | bool | Swiss-Prot / TrEMBL |
| sequence-length | int64 | Длина последовательности |
| sequence-mass | int64 | Масса (Да) |
| target-chembl-id | string | Входной ChEMBL target ID |
| taxonomy-id | int64 | NCBI Taxonomy ID |
| uniprot-accession | string | UniProt accession (выход) |
| uniprot-entry-name | string | Entry name |

## PubMed

### pubmed-publication
| Поле | Тип | Описание |
|---|---|---|
| -lookup-method | string | Метод поиска (direct/doi/pmid/title-fallback/unknown) |
| -original-id | string | Идентификатор запроса |
| abstract | string | Аннотация |
| abstract-structured | bool | Есть ли структурированные секции |
| affiliation-list | string | Уникальные аффилиации (JSON) |
| affiliation-structured | string | Структурированные аффилиации (ROR/GRID) |
| author-count | int64 | Кол-во авторов |
| authors | string | Список авторов (JSON) |
| authors-with-affiliations | string | Авторы с аффилиациями (JSON) |
| chemical-count | int64 | Кол-во хим. веществ |
| chemicals | string | Вещества (JSON) |
| citation-subset | string | Citation subset codes |
| citations-made | int64 | Исходящие ссылки |
| country | string | Страна публикации |
| databanks | string | Датабанки (JSON) |
| date-completed | string | Дата завершения MEDLINE обработки |
| date-revised | string | Дата ревизии записи |
| doi | string | DOI |
| gene-symbols | string | Ген-символы (JSON) |
| grant-count | int64 | Кол-во грантов |
| issn | string | ISSN |
| issue | string | Номер выпуска |
| journal | string | Название журнала |
| journal-iso-abbrev | string | ISO аббревиатура журнала |
| journal-issn-type | string | Тип ISSN (Print/Electronic/Linking) |
| journal-name-short | string | Короткое имя журнала |
| keyword-count | int64 | Кол-во ключевых слов |
| language | string | Язык |
| medline-pgn | string | Оригинальная пагинация |
| mesh-heading-count | int64 | Кол-во MeSH терминов |
| nlm-unique-id | string | NLM catalog ID |
| page-first | string | Первая страница |
| page-last | string | Последняя страница |
| page-range | string | Диапазон страниц |
| pmc-id | string | PubMed Central ID |
| pmid | string | PubMed ID |
| pub-date | string | Дата публикации (сырье) |
| pub-day | int64 | День публикации |
| pub-month | int64 | Месяц публикации |
| publication-class | string | Класс L1 |
| publication-date | string | Дата (YYYY-MM-DD) |
| publication-status | string | Статус (`ppublish`/`epublish`/`aheadofprint`) |
| publication-subclass | string | Подкласс L2 |
| publication-type | string | Тип (unified) |
| publication-type-list | string | Список типов (JSON) |
| publication-type-unified | string | Тип L3 |
| publication-types | list<string> | Типы (список) |
| publication-year | int64 | Год |
| subject-keywords | list<string> | Авторские ключевые слова |
| subject-mesh | list<string> | MeSH термины |
| title | string | Заголовок |
| volume | string | Том |

## CrossRef

### crossref-publication
| Поле | Тип | Описание |
|---|---|---|
| -lookup-method | string | direct/doi/pmid/title-fallback/unknown |
| -original-id | string | Исходный идентификатор |
| abstract | string | Аннотация (часто null) |
| affiliation-list | string | Аффилиации (часто null) |
| alternative-id | list<string> | Альтернативные ID издателя |
| author-details | string | JSON авторов |
| author-orcids | string | ORCID (JSON) |
| authors | string | Список авторов (JSON) |
| citations-made | int64 | references-count (исходящие) |
| citations-received | int64 | is-referenced-by-count (входящие) |
| content-domain-crossmark-restriction | bool | Ограничения Crossmark |
| content-domain-domains | list<string> | Домены контента |
| doi | string | DOI (PK) |
| issn | string | ISSN |
| issn-electronic | string | Электронный ISSN |
| issn-list | string | Все ISSN (JSON) |
| issn-print | string | Печатный ISSN |
| issue | string | Выпуск |
| journal | string | Журнал |
| journal-name-short | string | Короткое имя журнала |
| language | string | Язык |
| license-url | string | URL лицензии |
| page-first | string | Первая страница |
| page-last | string | Последняя страница |
| pmc-id | string | PMC ID (обычно null) |
| pmid | string | PMID (обычно null) |
| publication-class | string | Класс L1 |
| publication-date | string | Дата (YYYY-MM-DD) |
| publication-subclass | string | Подкласс L2 |
| publication-type | string | Тип CrossRef (raw type) |
| publication-type-unified | string | Тип L3 |
| publication-year | int64 | Год |
| published | string | Каноническая дата публикации |
| published-online | string | Дата онлайн публикации |
| published-print | string | Дата печати |
| publisher | string | Издатель |
| references | string | JSON массива ссылок |
| subject-keywords | list<string> | Ключевые слова |
| title | string | Заголовок |
| volume | string | Том |

## OpenAlex

### openalex-publication
| Поле | Тип | Описание |
|---|---|---|
| -lookup-method | string | direct/doi/pmid/title-fallback/unknown |
| -original-id | string | Исходный ID |
| abstract | string | Аннотация |
| affiliation-list | string | Аффилиации (JSON) |
| author-openalex-ids | string | OpenAlex IDs авторов (JSON) |
| author-orcids | string | ORCID авторов (JSON) |
| authors | string | Список авторов (JSON) |
| citations-made | int64 | Кол-во ссылок (referenced-works-count) |
| citations-received | int64 | Кол-во цитирований (cited-by-count) |
| doi | string | DOI |
| fwci | float64 | Field-Weighted Citation Impact |
| grants | string | Гранты (JSON) |
| institution-country-codes | list<string> | Коды стран организаций |
| institution-ids | list<string> | ID организаций |
| is-oa | bool | Open access |
| is-retracted | bool | Флаг отзыва |
| issn | string | ISSN |
| issue | string | Выпуск |
| journal | string | Журнал |
| language | string | Язык |
| mag-id | string | Microsoft Academic Graph ID |
| oa-status | string | OA статус |
| openalex-id | string | PK OpenAlex |
| page-first | string | Первая страница |
| page-last | string | Последняя страница |
| pmc-id | string | PMC ID (обычно null) |
| pmid | string | PMID (если есть) |
| primary-topic | string | Основная тема (JSON) |
| publication-class | string | Класс L1 |
| publication-date | string | Дата (YYYY-MM-DD) |
| publication-subclass | string | Подкласс L2 |
| publication-type | string | Тип OpenAlex (article/book/...) |
| publication-type-unified | string | Тип L3 |
| publication-year | int64 | Год |
| publisher | string | Издатель |
| ror-ids | string | ROR ID организаций (JSON) |
| subject-keywords | list<string> | Ключевые слова |
| subject-mesh | list<string> | MeSH (если есть) |
| subject-topics | string | Темы (JSON) |
| title | string | Заголовок |
| volume | string | Том |

## Semantic Scholar

### semanticscholar-publication
| Поле | Тип | Описание |
|---|---|---|
| -lookup-method | string | Метод поиска |
| -original-id | string | Исходный ID |
| abstract | string | Аннотация |
| affiliation-list | string | Аффилиации (JSON) |
| author-h-indices | string | h-index авторов (JSON) |
| author-orcids | string | ORCID (JSON) |
| author-s2-ids | string | S2 IDs авторов (JSON) |
| citation-contexts | string | Контексты цитирования (JSON) |
| citations-made | int64 | Кол-во ссылок (referenceCount) |
| citations-received | int64 | Кол-во цитирований (citationCount) |
| corpus-id | int64 | Corpus ID |
| dblp-id | string | DBLP ID |
| doi | string | DOI |
| influential-citation-count | int64 | Влиятельные цитаты |
| is-oa | bool | Open access |
| issue | string | Выпуск |
| journal | string | Журнал |
| oa-status | string | OA статус |
| open-access-url | string | OA URL |
| page-first | string | Первая страница |
| page-last | string | Последняя страница |
| page-range | string | Диапазон страниц |
| paper-id | string | PK Semantic Scholar |
| pmc-id | string | PMC ID |
| pmid | string | PMID |
| publication-class | string | Класс L1 |
| publication-date | string | Дата |
| publication-subclass | string | Подкласс L2 |
| publication-type | string | Тип (joined publicationTypes) |
| publication-type-unified | string | Тип L3 |
| publication-types | string | Исходный список типов (JSON) |
| publication-year | int64 | Год |
| subject-fields | string | Тематические поля |
| title | string | Заголовок |
| tldr | string | Краткое summary |
| volume | string | Том |

## Системные и DQ поля (общие)
- `entity-id`: бизнес-ключ записи (строка).
- `content-hash`: SHA256 содержимого для дедупликации.
- `-run-id`, `-run-type`: идентификатор и тип запуска пайплайна.
- `-source-batch-id`: ID партии источника.
- `-source`: идентификатор провайдера (есть не во всех схемах).
- `-ingestion-ts`: метка загрузки (UTC, ISO-8601 как строка).
- `-index`: порядковый номер записи в партии.
- `-dq-error`, `-dq-warn`: флаги контроля качества (True/False).


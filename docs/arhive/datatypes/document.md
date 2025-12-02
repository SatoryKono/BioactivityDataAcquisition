# Document fields

| field_name           | data_type | is_nullable | is_filterable | description                                                       | example_value                 | notes |
|----------------------|----------|------------|--------------|-------------------------------------------------------------------|-------------------------------|-------|
| abstract             | string   | yes        | yes?         | Аннотация документа                                               | null                          | Может быть большой текст. |
| authors              | string   | yes        | yes?         | Строка с авторами                                                 | Clader JW.                    | |
| doc_type             | string   | no         | yes          | Тип документа: PUBLICATION, DATASET, PATENT и т.п.                | PUBLICATION                   | |
| document_chembl_id   | string   | no         | yes          | ChEMBL ID документа                                               | CHEMBL1139451                 | Основной ID в API. |
| doi                  | string   | yes        | yes          | DOI публикации                                                    | 10.1021/jm030283g             | |
| doi_chembl           | string   | yes        | ?            | Внутренний DOI ChEMBL для датасетов                               | null                          | Используется для deposited datasets. |
| first_page           | string   | yes        | ?            | Первая страница                                                   | 1                             | Строка, не число. |
| issue                | string   | yes        | ?            | Номер выпуска                                                     | 1                             | |
| journal              | string   | yes        | yes          | Сокращённое название журнала                                     | J. Med. Chem.                 | |
| journal_full_title   | string   | yes        | ?            | Полное название журнала                                          | Journal of medicinal chemistry. | |
| last_page            | string   | yes        | ?            | Последняя страница                                                | 9                             | |
| patent_id            | string   | yes        | yes          | Идентификатор патента                                             | null                          | Для doc_type=PATENT. |
| pubmed_id            | string   | yes        | yes          | PubMed ID                                                         | 14695813                      | Строка. |
| src_id               | integer  | yes        | yes          | ID источника (журнал, WDI, deposited и т.п.)                      | 1                             | Связь с `/source`. |
| title                | string   | no         | yes          | Заголовок статьи/документа                                       | The discovery of ezetimibe: ... | |
| volume               | string   | yes        | ?            | Том                                                               | 47                            | |
| year                 | integer  | yes        | yes          | Год публикации                                                    | 2004                          | |
| chembl_release_id    | integer  | yes        | ?            | ID релиза ChEMBL, в котором документ появился                     | 36                            | Требует проверки по `/schema`. |

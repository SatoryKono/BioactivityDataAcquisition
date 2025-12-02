# Cell Line fields

| field_name          | data_type | is_nullable | is_filterable | description                                                  | example_value        | notes |
|---------------------|----------|------------|--------------|--------------------------------------------------------------|----------------------|-------|
| cell_chembl_id      | string   | no         | yes          | ChEMBL ID клеточной линии                                   | CHEMBL3307241        | Основной внешний ID. |
| cell_name           | string   | yes        | yes?         | Название клеточной линии                                    | HepG2                | Имя поля по аналогии; проверить `/schema`. |
| cell_source_organism| string   | yes        | yes          | Организм-источник                                           | Homo sapiens         | |
| cell_source_tax_id  | integer  | yes        | yes          | NCBI TaxID организма                                        | 9606                 | |
| cell_source_tissue  | string   | yes        | yes          | Ткань-источник                                              | lung carcinoma       | Используется в фильтрации `__iendswith`. |
| cellosaurus_id      | string   | yes        | yes          | ID в Cellosaurus                                            | CVCL_4704            | |
| cl_lincs_id         | string   | yes        | ?            | Идентификатор LINCS                                         | null                 | Часто пустой. |
| clo_id              | string   | yes        | ?            | ID в Cell Line Ontology (CLO)                               | CLO_0001234          | Имя поля видно в XML. |
| efo_id              | string   | yes        | ?            | ID в Experimental Factor Ontology                           | EFO:0001187          | |

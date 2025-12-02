# Compound Record fields

| field_name          | data_type | is_nullable | is_filterable | description                                                               | example_value     | notes |
|---------------------|----------|------------|--------------|---------------------------------------------------------------------------|-------------------|-------|
| record_id           | integer  | no         | yes          | Внутренний ID записи COMPOUND_RECORD (RIDX/CIDX, нормализованный)        | 206172            | Используется как FK из `activity`. |
| molecule_chembl_id  | string   | no         | yes          | ChEMBL ID молекулы                                                       | CHEMBL113081      | |
| document_chembl_id  | string   | no         | yes          | ChEMBL ID документа                                                      | CHEMBL1137930     | |
| src_id              | integer  | yes        | yes          | Источник записи (депозитор / происхождение)                              | 1                 | |
| compound_name       | string   | yes        | yes?         | Название соединения в рамках документа                                   | Compound 12a      | Имя поля по стилю REST; сверить по `/schema`. |

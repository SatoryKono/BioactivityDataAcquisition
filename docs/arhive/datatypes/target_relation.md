# Target Relation fields

| field_name            | data_type | is_nullable | is_filterable | description                                                          | example_value      | notes |
|-----------------------|----------|------------|--------------|----------------------------------------------------------------------|--------------------|-------|
| target_relation_id    | integer  | no         | yes?         | Внутренний ID записи отношения между таргетами                       | 12345              | Имя и наличие PK нужно подтвердить по `/schema`. |
| target_chembl_id      | string   | no         | yes          | ChEMBL ID «основного» таргета                                       | CHEMBL2251         | |
| related_target_chembl_id | string | no        | yes?         | ChEMBL ID связанного таргета                                        | CHEMBL240          | Имя поля по смыслу; сверить со схемой. |
| relationship          | string   | no         | yes?         | Тип отношения (PARENT_OF, CHILD_OF, GROUP_MEMBER и т.п.)            | PARENT_OF          | Список значений известен по SQL-схеме ChEMBL. |

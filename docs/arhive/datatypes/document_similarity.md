# Document Similarity fields

| field_name            | data_type | is_nullable | is_filterable | description                                                        | example_value         | notes |
|-----------------------|----------|------------|--------------|--------------------------------------------------------------------|-----------------------|-------|
| document_1_chembl_id  | string   | no         | yes          | ChEMBL ID исходного документа, для которого ищутся похожие        | CHEMBL1122254         | Подтверждено как параметр запроса. |
| document_2_chembl_id  | string   | no         | ?            | ChEMBL ID документа, признанного похожим на исходный              | CHEMBL1148466         | Имя выведено по смыслу; проверить в `/schema`. |

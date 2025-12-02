# Target fields

| field_name         | data_type | is_nullable | is_filterable | description                                                        | example_value                     | notes |
|--------------------|----------|------------|--------------|--------------------------------------------------------------------|-----------------------------------|-------|
| target_chembl_id   | string   | no         | yes          | ChEMBL ID таргета                                                  | CHEMBL2074                        | Основной внешний ID. |
| pref_name          | string   | yes        | yes          | Название таргета                                                   | Maltase-glucoamylase             | |
| organism           | string   | yes        | yes          | Организм                                                           | Homo sapiens                      | |
| target_type        | string   | no         | yes          | Тип таргета: SINGLE PROTEIN, PROTEIN FAMILY, ORGANISM и т.п.      | SINGLE PROTEIN                    | |
| tax_id             | integer  | yes        | yes          | NCBI TaxID                                                         | 9606                              | |
| species_group_flag | boolean  | yes        | ?            | Флаг «группового» таргета по видам                                | False                             | |
| target_components  | array    | yes        | no           | Компоненты таргета (UniProt-последовательности и др.)             | [{"accession": "O43451", ...}]| Вложенные объекты. |
| cross_references   | array    | yes        | ?            | Внешние кросс-референсы                                           | [{"xref_id": "O43451", ...}] | UniProt, canSAR и т.п. |

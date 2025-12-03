# Target (`target`)

| Поле | Тип данных | Допустимые значения | Описание |
|------|------------|----------------------|----------|
| target_chembl_id | строка | — | ChEMBL ID таргета. |
| pref_name | строка | — | Курируемое имя таргета. |
| organism | строка | — | Организм, к которому относится таргет. |
| tax_id | целое (int) | — | NCBI Taxonomy ID организма. |
| target_type | строка | — | Тип таргета (SINGLE PROTEIN, PROTEIN FAMILY и т.д.). |
| species_group_flag | логическое | true/false | Является ли таргет группой видов. |
| score | число (float) | — | Score, используемый при поиске. |
| target_components | список объектов | — | Компоненты таргета (белки, ДНК и др.). |
| cross_references | список объектов | — | Внешние ссылки (UniProt, GO, Reactome и др.). |

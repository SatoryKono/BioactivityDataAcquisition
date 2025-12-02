# Molecule fields

## Верхний уровень

| field_name            | data_type | is_nullable | is_filterable | description                                                   | example_value          | notes |
|-----------------------|----------|------------|--------------|---------------------------------------------------------------|------------------------|-------|
| molecule_chembl_id    | string   | no         | yes          | ChEMBL ID молекулы                                           | CHEMBL6329             | Основной внешний ID. |
| pref_name             | string   | yes        | yes          | Название молекулы                                            | IMATINIB               | Может быть null. |
| molecule_type         | string   | yes        | yes          | Тип: Small molecule, Antibody, Oligonucleotide и т.п.        | Small molecule         | |
| max_phase             | integer  | yes        | yes          | Максимальная клиническая фаза                               | 4                      | 0–4. |
| structure_type        | string   | yes        | ?            | Формат структуры: MOL, SMILES и т.п.                        | MOL                    | |
| molecule_properties   | object   | yes        | yes          | Вложенный объект со свойствами (логP, формула, масса и т.п.) | {...}                  | Фильтрация через nested-путь. |
| molecule_structures   | object   | yes        | yes          | Вложенный объект с SMILES, InChI, molfile                   | {...}                  | |
| molecule_hierarchy    | object   | yes        | no           | Родитель/дозируемая форма и др.                             | {"parent_chembl_id": "CHEMBL1"} | |
| atc_classifications   | array    | yes        | yes          | Список ATC-классификаций                                    | [{"level1": "C", ...}] | |
| helm_notation         | string   | yes        | ?            | HELM-нотация для биотерапевтических молекул                 | null                   | |

## molecule_properties

| field_name        | data_type | is_nullable | is_filterable | description                               | example_value          | notes |
|-------------------|----------|------------|--------------|-------------------------------------------|------------------------|-------|
| alogp             | number   | yes        | yes          | Липофильность (ALOGP)                     | 2.11                   | |
| aromatic_rings    | integer  | yes        | yes          | Количество ароматических колец            | 3                      | |
| full_molformula   | string   | yes        | yes          | Полная молекулярная формула               | C17H12ClN3O3           | |
| full_mwt          | number   | yes        | yes          | Молекулярная масса                        | 341.75                 | |

## molecule_structures

| field_name        | data_type | is_nullable | is_filterable | description                           | example_value                      | notes |
|-------------------|----------|------------|--------------|---------------------------------------|------------------------------------|-------|
| canonical_smiles  | string   | no         | yes?         | Канонический SMILES                  | Cc1cc(-n2ncc(=O)[nH]...)           | Структурный поиск обычно через спец. ресурсы. |
| molfile           | string   | yes        | no           | MOLFILE-представление структуры      | ...                                | Большой многострочный блок. |
| standard_inchi    | string   | yes        | yes          | Стандартный InChI                    | InChI=1S/C17H12ClN3O3/...          | |
| standard_inchi_key| string   | yes        | yes          | InChIKey                             | GHBOEFUAGSHXPO-XZOTUCIWSA-N        | |

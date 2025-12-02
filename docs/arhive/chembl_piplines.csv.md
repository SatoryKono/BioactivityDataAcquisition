# chembl_piplines.csv

|  | Extract (, ) | Transform (  ) | Validate (Pandera schema) |  Write ( ) |
| --- | --- | --- | --- | --- |
| Activity | GET /activity  ChEMBL. : activity_id, molecule_chembl_id, assay_chembl_id, target_chembl_id, document_chembl_id | -  -  ligand_efficiency-    activity_id | ActivitySchema |      |
| Assay | GET /assay  ChEMBL. : assay_chembl_id, target_chembl_id, document_chembl_id | -   (confidence_score  .)-  -    ( )-   assay_type  assay_chembl_id | AssaySchema |  writer,     |
| TestItem | GET /molecule  ChEMBL. : molecule_chembl_id, parent_molecule_chembl_id | -  -  molecule_properties  molecule_structures-   molecule_chembl_id-  enrichment  PubChem | TestItemSchema |    .  |
| Target | GET /target  ChEMBL. : target_chembl_id, target_type, pref_name, organism, target_components, cross_references | -   (tax_id, species_group_flag)-  -    -    target_type  ID | TargetSchema |   PipelineBase |
| Document | GET /document  ChEMBL. : document_chembl_id, doi, pubmed_id, patent_id, title, doc_type, authors, journal, year | -  -     -   doc_type ? patent_id-    ID, title, doc_type | DocumentSchema +   PATENT |     |
|  |  |  |  |  |
|  ,       Markdown, CSV  Pandas DataFrame. |  |  |  |  |

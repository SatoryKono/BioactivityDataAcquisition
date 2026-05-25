# Non-ChEMBL Observed Value Inventory

- source: `tracked_non_chembl_bronze_fixtures_and_vcr_derived_edge_samples`
- observed_fixture_path: `tests/fixtures/normalization/non_chembl_observed_values.yaml`

## Sections

### publication_nested_vocab

```json
{
  "openalex": {
    "indexed_in": [
      "crossref",
      "doaj",
      "pubmed"
    ],
    "license": [
      "cc-by",
      "cc-by-nc-nd",
      "cc-by-sa",
      "other-oa"
    ],
    "oa_status": [
      "closed",
      "diamond",
      "gold",
      "green",
      "hybrid"
    ],
    "raw_type": [
      "journal-article",
      "monograph",
      "posted-content",
      "proceedings-article",
      "text"
    ],
    "source_type": [
      "ebook platform",
      "journal",
      "repository"
    ],
    "version": [
      "publishedVersion",
      "submittedVersion"
    ]
  },
  "pubmed": {
    "affiliation_keys": [
      "affiliations",
      "author",
      "collective_name"
    ],
    "mesh_keys": [
      "descriptor_name",
      "descriptor_ui",
      "is_major_topic",
      "qualifier_name",
      "qualifier_ui"
    ],
    "publication_types": [
      "Clinical Trial",
      "Journal Article",
      "Meta-Analysis",
      "Review"
    ]
  },
  "semanticscholar": {
    "author_id_families": [
      "CorpusId",
      "DBLP",
      "ORCID",
      "OpenAlex"
    ],
    "citation_context_keys": [
      "contexts",
      "intent",
      "isInfluential",
      "section"
    ],
    "publication_types": [
      "ClinicalTrial",
      "JournalArticle",
      "Review"
    ],
    "subject_fields": [
      "Bioinformatics",
      "Biology",
      "Chemistry",
      "Data Engineering",
      "Data Science",
      "Genomics",
      "Knowledge Graphs",
      "Machine Learning",
      "Medicine",
      "Observability",
      "Physics",
      "Reproducibility",
      "Systems Biology"
    ]
  }
}
```

### crossref_publication_types

```json
[
  "book-chapter",
  "journal-article",
  "posted-content"
]
```

### uniprot_semantic_payloads

```json
{
  "comment_types": [
    "ALTERNATIVE PRODUCTS",
    "CATALYTIC ACTIVITY",
    "CAUTION",
    "COFACTOR",
    "DISEASE",
    "FUNCTION",
    "INDUCTION",
    "PATHWAY",
    "SIMILARITY",
    "SUBCELLULAR LOCATION",
    "SUBUNIT",
    "TISSUE SPECIFICITY"
  ],
  "feature_types": [
    "Active site",
    "Binding site",
    "Domain",
    "Modified residue"
  ],
  "keyword_categories": [
    "Biological process",
    "Cellular component",
    "Coding sequence diversity",
    "Disease",
    "Domain",
    "Ligand",
    "Molecular function",
    "PTM",
    "Technical term"
  ]
}
```

### uniprot_idmapping

```json
{
  "all_mappings_expected_normalized": [
    "CHEMBL203",
    "P00742",
    "Q9Y6K9"
  ],
  "mapping_status": [
    "error",
    "found",
    "multiple",
    "not_found"
  ]
}
```

### pubchem_property_vocab

```json
{
  "datatype": [
    "1",
    "16",
    "5",
    "7"
  ],
  "implementation": [
    "E_COMPLEXITY",
    "E_NHACCEPTORS",
    "E_NHDONORS",
    "E_NROTBONDS",
    "E_SCREEN",
    "E_TPSA"
  ],
  "label": [
    "Compound",
    "Compound Complexity",
    "Count",
    "Fingerprint",
    "IUPAC Name",
    "InChI",
    "InChIKey",
    "Log P",
    "Mass",
    "Molecular Formula",
    "Molecular Weight",
    "SMILES",
    "Topological",
    "Weight"
  ],
  "name": [
    "Absolute",
    "Allowed",
    "CAS-like Style",
    "Canonicalized",
    "Connectivity",
    "Exact",
    "Hydrogen Bond Acceptor",
    "Hydrogen Bond Donor",
    "Markup",
    "MonoIsotopic",
    "Polar Surface Area",
    "Preferred",
    "Rotatable Bond",
    "Standard",
    "SubStructure Keys",
    "Systematic",
    "Traditional",
    "XLogP3",
    "XLogP3-AA"
  ],
  "release": [
    "2025.04.14",
    "2025.06.30",
    "2025.09.15"
  ],
  "software": [
    "Cactvs",
    "InChI",
    "Lexichem TK",
    "OEChem",
    "PubChem"
  ],
  "source": [
    "OpenEye Scientific Software",
    "Xemistry GmbH",
    "iupac.org",
    "ncbi.nlm.nih.gov",
    "sioc-ccbg.ac.cn"
  ]
}
```

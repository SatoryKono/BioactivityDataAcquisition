# JSON Field Typing Inventory (Bronze -> Silver -> Gold)

Scope: inferred Bronze CSV samples + Silver Pandera + Silver PyArrow + Gold contracts.

| Field | Bronze inferred | Silver Pandera | Silver PyArrow | Gold contract |
| --- | --- | --- | --- | --- |
| `-ingestion-ts` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `-lookup-method` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `-original-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `-run-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `-run-type` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `-source` | `unknown` (nullable) | — | `string` (nullable) | `str` (not-null) |
| `-source-batch-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `abstract` | `null` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `accession` | `null|string` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `acetylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `action-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `action-type-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `action-type-parent-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `active-sites` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity-comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity-id` | `integer` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `activity-properties` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity-regulation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `affiliation-list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `affiliation-structured` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `aidx` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `all-mappings` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `alternative-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `alternative-products` | `unknown` (nullable) | `str` (nullable) | — | — |
| `assay-category` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-cell-type` | `integer|null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-group` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `assay-organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-parameters` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-pref-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-strain` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-subcellular-fraction` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-test-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-tissue` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-type-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-variant-accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay-variant-mutation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `atc-classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-details` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-h-indices` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-keys` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-openalex-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-orcids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author-s2-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `authors` | `null|string` (nullable) | `str` (nullable) | — | `str` (nullable) |
| `authors-with-affiliations` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao-endpoint` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao-format` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao-label` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `binding-sites` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `biophysicochemical-properties` | `unknown` (nullable) | `str` (nullable) | — | — |
| `canonical-smiles` | `array|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `catalytic-activity` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `caution` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cell-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `cell-name` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `cell-source-organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell-source-tissue` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell-type` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cellosaurus-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cellular-component` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `chembl-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `chembl-release` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `chemicals` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `citation-contexts` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `citation-subset` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cl-lincs-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `clo-id` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cofactors` | `unknown` (nullable) | `str` (nullable) | — | — |
| `comments` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component-accessions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component-descriptions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `component-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component-relationships` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component-types` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `compound-key` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `compound-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `confidence-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `content-domain-domains` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `content-hash` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `country` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `creation-date` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cross-references` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `data-validity-comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `data-validity-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `databanks` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `date-completed` | `unknown` (nullable) | `datetime64[ns]` (nullable) | `string` (nullable) | `str` (nullable) |
| `date-revised` | `unknown` (nullable) | `datetime64[ns]` (nullable) | `string` (nullable) | `str` (nullable) |
| `dblp-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `definition` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `description` | `array|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `disease-involvement` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `disulfide-bond` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `doi` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `domains` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `drugbank-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `efo-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `entity-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `entry-name` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (nullable) |
| `entry-type` | `unknown` (nullable) | `str` (nullable) | — | — |
| `features-json` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `flag` | `unknown` (nullable) | `str` (nullable) | — | — |
| `function-comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene-names` | `unknown` (nullable) | — | `list<item: string>` (nullable) | `str` (nullable) |
| `gene-orf-names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `gene-primary` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene-symbols` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene-synonyms` | `unknown` (nullable) | `str` (nullable) | — | — |
| `genus` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `glycosylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `go-terms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `grants` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `guidetopharmacology-ids` | `unknown` (nullable) | `str` (nullable) | — | — |
| `helm-notation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy-active-chembl-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy-child-chembl-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy-parent-chembl-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `inchi` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `inchi-key` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `induction` | `unknown` (nullable) | `str` (nullable) | — | — |
| `institution-country-codes` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `institution-ids` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `interpro-xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `intramembrane` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `isoform-ids` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `isoform-names` | `integer|null|string` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `isoform-synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `isomeric-smiles` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn-electronic` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn-list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn-print` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issue` | `integer|null` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `iupac-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal-iso-abbrev` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal-issn-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal-name-short` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `keywords` | `unknown` (nullable) | `str` (nullable) | — | — |
| `language` | `unknown` (nullable) | `str` (nullable) | — | — |
| `license-url` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `lineage` | `unknown` (nullable) | `str` (nullable) | — | — |
| `lipidation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `logp-method` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mag-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mapping-status` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `medline-pgn` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mesh-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mid` | `unknown` (nullable) | `str` (nullable) | — | `str` (nullable) |
| `modified-residue` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `molecular-formula` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecular-function` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `molecule-hierarchy` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `molecule-pref-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-properties` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-species` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-structures` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule-type` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `nlm-unique-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `oa-status` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `open-access-url` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `openalex-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `organism` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `organism-common` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `organism-scientific` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page-first` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page-last` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page-range` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `paper-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `parent-molecule-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pathway` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pdb-xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pfam-xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pharmaceutical-use` | `unknown` (nullable) | `str` (nullable) | — | — |
| `phosphorylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `phylum` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `pii` | `unknown` (nullable) | `str` (nullable) | — | `str` (nullable) |
| `pipeline-stages` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pmc-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `pmid` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pref-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `primary-topic` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `propeptide` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `protein-alternative-names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `protein-class-desc` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein-classification-ids` | `integer|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein-classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein-ec-numbers` | `unknown` (nullable) | `str` (nullable) | — | — |
| `protein-existence` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein-short-names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `pub-date` | `unknown` (nullable) | — | `string` (nullable) | — |
| `publication-class` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `publication-date` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication-doi` | `unknown` (nullable) | — | — | `str` (nullable) |
| `publication-id` | `string` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `publication-pmc-id` | `unknown` (nullable) | — | — | `str` (nullable) |
| `publication-pmid` | `unknown` (nullable) | — | — | `str` (nullable) |
| `publication-status` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication-subclass` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `publication-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication-type-list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication-type-unified` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `publication-types` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published-online` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published-print` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publisher` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publisher-id` | `unknown` (nullable) | `str` (nullable) | — | `str` (nullable) |
| `pubmed-id1` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pubmed-id2` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `qualifier` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `qudt-units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `reaction-ec-numbers` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `reactions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `reactome-xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `references` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relationship-description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relationship-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `ro3-pass` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `ror-ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `secondary-accessions` | `unknown` (nullable) | `str` (nullable) | — | — |
| `sequence` | `unknown` (nullable) | `str` (not-null) | — | — |
| `sequence-checksum` | `unknown` (nullable) | `str` (nullable) | — | — |
| `short-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `signal-peptide` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `similarity-comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `src-assay-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `src-compound-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard-inchi` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard-relation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard-text-value` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard-units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `structure-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subcellular-location` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subject-fields` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subject-keywords` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `subject-mesh` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `subject-topics` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subunit` | `unknown` (nullable) | `str` (nullable) | — | — |
| `superkingdom` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `target-component-synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target-component-xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target-components` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target-id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `target-organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target-pref-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target-type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `term` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `term-type` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `text-value` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tissue-id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tissue-specificity` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `title` | `array|null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tldr` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `topology` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `transmembrane` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (not-null) |
| `ubiquitination` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | — |
| `uniprot-accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `uniprot-entry-name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `uo-units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan-stem` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan-stem-definition` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan-substem` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-isoform` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-mutation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-sequence` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant-sequence-json` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `volume` | `integer|null` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |

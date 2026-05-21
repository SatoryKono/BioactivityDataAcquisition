# BioETL: аудит нормализации данных во всех non-ChEMBL пайплайнах по current `main`

Дата генерации: 2026-05-12  
Режим: архитектурно-строгий static audit по current repository state.  
Ограничение: live provider APIs не вызывались; использованы registry/configs/contracts/tests/fixtures/VCR/runtime governance artifacts из репозитория.  

## TL;DR

Текущее состояние non-ChEMBL normalization в BioETL на `main` в целом ближе к `mostly pass with P1 hardening`, чем к structural failure.

Установленные факты:

- Все 7 non-ChEMBL entity pipelines зарегистрированы в отдельном manifest registry, имеют entity configs, Silver schemas и active Gold contracts: `pubchem_compound`, `uniprot_protein`, `uniprot_idmapping`, `pubmed_publication`, `crossref_publication`, `openalex_publication`, `semanticscholar_publication` [N1][N3].
- Все 7 имеют tracked Bronze fixture coverage; у 5 из них есть edge fixtures; VCR cassette coverage существует у всех 6 non-ChEMBL providers/families [N2][N18][N23].
- Для publication family уже есть явное разделение между raw provider type surfaces и derived harmonized taxonomy:
  `publication_type` остаётся open-world provider value, а `publication_type_unified` / `publication_subclass` / `publication_class` нормализуются через общий classification layer [N4][N8][N9][N10][N11][N18].
- Для identifier canonicalization уже есть общий domain-pure registry `reference_ids.py`, покрывающий DOI, PMID, PMCID, ORCID, ISSN, OpenAlex IDs, UniProt accessions, GO, InterPro, Pfam, Reactome, PDB, ROR, DrugBank и ChEMBL IDs [N5].
- Для semantic-sensitive JSON/structured payloads уже есть явные policy registries:
  `publication_structured_fields.py` и `structured_payload_policies.py`, включая raw sidecar / canonical sidecar contracts и collection semantics [N6][N7].

Главные остаточные риски:

- Publication-family governance уже сильный, но не полностью симметричный: OpenAlex, PubMed и Semantic Scholar имеют явный dual-field strategy для semantic-sensitive payloads, а CrossRef остаётся более “плоским” и слабее формализует structured/reference payload semantics [N6][N9][N10][N11].
- PubChem normalization архитектурно чистая, но семантически тонкая: кроме identifiers, SMILES и `chemical_standardization_*`, большинство полей остаются generic scalar surfaces без provider-aware vocab/unit layer [N12][N18].
- UniProt protein имеет сильную identifier canonicalization и JSON envelope policy, но nested vocabulary governance пока точечная: отдельный registry есть только для `features_json` semantic payload families, не для всех feature/comment/xref subfamilies [N6][N13].
- Edge-fixture coverage неравномерна: у `crossref_publication` и `uniprot_protein` нет tracked edge Bronze fixtures в manifest, хотя у provider families есть VCR coverage. Это снижает confidence для observed-value inventory и regression gates [N2][N18][N23].
- Composite joins уже завязаны на canonical non-ChEMBL anchors, но drift в title fallback, mixed identifier sets и provider-type semantics всё ещё может дать silent null enrichment или uneven semantic merge, особенно в `composite_publication` и `composite_target` [N15][N16][N17].

Итоговая оценка:

- **Layer correctness**: pass.
- **Determinism / content-hash readiness**: mostly pass with P1 hardening.
- **Enum/vocabulary governance**: partially unified, strongest in publication family, weaker in PubChem and deep UniProt semantic payloads.
- **Composite-readiness of normalized anchors**: pass with targeted P1/P2 gap closure.

## 1. Метод и ограничения

- Проверены current-main runtime artifacts: pipeline registry manifests, entity configs, contract registry, domain normalization profiles, transformers, composite configs, tests, Bronze fixtures, edge fixtures, VCR cassettes, ADR/RULES governance [N1][N2][N3][N19][N20][N21][N22][N23].
- Для provider semantics использованы только локальные evidence surfaces: adapter/transformer contracts, VCR fixtures, tracked Bronze fixtures, observed-value inventories и config/docs registries.
- Live provider universes не извлекались. Поэтому `observed values` ниже означают observed-in-repo, а не complete provider universe.
- Поле не классифицировалось как strict enum только из-за низкой fixture cardinality. Для raw provider values приоритет отдавался registry/tests/policies, а не sample size alone [N4][N18].

## 2. Executive Summary

### 2.1. Что уже хорошо

- Non-ChEMBL pipelines structurally complete: registry, fixtures, contracts и core schemas согласованы [N1][N2][N3].
- Publication-family normalization уже имеет общий shared layer:
  DOI/PMID/ISSN/ORCID/ OpenAlex IDs / OA status / publication taxonomy [N4][N5][N8][N9][N10][N11].
- Structured JSON policy больше не “размазана” только по transformers: raw/canonical sidecars и ordering semantics вынесены в domain registries [N6][N7].
- Composite boundaries явно документированы и протестированы:
  `doi`/`pmid`/`title` для publication,
  `inchi_key`/`canonical_smiles` для molecule,
  `target_id -> uniprot_accession` для target [N15][N16][N17].

### 2.2. Где основная архитектурная слабость

- Non-ChEMBL normalization не является полностью единым layer. Она уже partially centralized, но сейчас распределена между:
  `reference_ids.py`,
  profile-specific rules,
  `publication_controlled.yaml`,
  `structured_payload_policies.py`,
  entity DQ configs,
  composite join-key tests [N4][N5][N6][N7][N8][N9][N10][N11][N12][N13][N14][N15][N16][N17].
- Publication providers архитектурно более зрелые, чем PubChem и UniProt:
  shared publication taxonomy и identifier seams уже формализованы, тогда как PubChem property semantics и глубокие UniProt nested vocabularies нормализуются слабее [N4][N12][N13].

### 2.3. Главные cross-provider риски

- Raw/source semantics и normalized analytical semantics уже разведены для publication type family, но не столь же системно разведены для nested JSON payload families и некоторых provider-specific status/type surfaces.
- Hash determinism для set-like/JSON-like fields mostly enforced, но persisted canonical representation и hash ordering policy не везде совпадают с одинаковой строгостью.
- Observed-value confidence неравномерен: tracked 20-record CI samples есть у всех, но edge fixtures есть не у всех, а provider universes существенно шире [N2][N18][N23].

## 3. Scope Inventory

| Pipeline | Provider | Entity | Registered? | Config exists? | Transformer exists? | Silver schema | Gold contract | Fixtures/VCR/sample coverage | Included? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `pubchem_compound` | `pubchem` | `compound` | yes [N1] | yes [N12] | yes [N12] | yes [N1] | active [N3] | tracked CI 20 + edge + VCR [N2][N23] | yes | non-ChEMBL chemical reference family |
| `uniprot_protein` | `uniprot` | `protein` | yes [N1] | yes [N13] | yes [N13] | yes [N1] | active [N3] | tracked CI 20 + VCR [N2][N23] | yes | no tracked edge Bronze fixture in manifest |
| `uniprot_idmapping` | `uniprot` | `idmapping` | yes [N1] | yes [N14] | yes [N14] | yes [N1] | active [N3] | tracked CI 20 + edge + VCR [N2][N23] | yes | bridge pipeline for composite target |
| `pubmed_publication` | `pubmed` | `publication` | yes [N1] | yes [N8] | yes [N8] | yes [N1] | active [N3] | tracked CI 20 + edge + VCR [N2][N23] | yes | strongest MeSH/affiliation structured sidecars |
| `crossref_publication` | `crossref` | `publication` | yes [N1] | yes [N9] | yes [N9] | yes [N1] | active [N3] | tracked CI 20 + VCR [N2][N23] | yes | has deprecated alias `crossref.works` contract entry [N3] |
| `openalex_publication` | `openalex` | `publication` | yes [N1] | yes [N10] | yes [N10] | yes [N1] | active [N3] | tracked CI 20 + edge + VCR [N2][N23] | yes | strongest topic/grants dual-field strategy |
| `semanticscholar_publication` | `semanticscholar` | `publication` | yes [N1] | yes [N11] | yes [N11] | yes [N1] | active [N3] | tracked CI 20 + edge + VCR [N2][N23] | yes | richest raw/canonical payload inventory after PubMed/OpenAlex |
| `composite_publication` | `composite` | `publication` | config-only [N15] | yes [N15] | composite runtime | merged Silver/Gold | composite contract surface | join-key tests + config tests [N15] | yes | non-ChEMBL enrichers: CrossRef/OpenAlex/PubMed/Semantic Scholar |
| `composite_molecule` | `composite` | `molecule` | config-only [N16] | yes [N16] | composite runtime | merged Silver/Gold | composite contract surface | boundary tests [N16] | yes | non-ChEMBL enricher: PubChem only |
| `composite_target` | `composite` | `target` | config-only [N17] | yes [N17] | composite runtime | merged Silver/Gold | composite contract surface | boundary tests [N17] | yes | non-ChEMBL dependencies: UniProt IDMapping + Protein |
| `composite_activity` | `composite` | `activity` | config-only [N24] | yes [N24] | composite runtime | merged Silver/Gold | composite contract surface | config only [N24] | excluded | current `main` uses only ChEMBL dependencies; comment mentions future PubChem/UniProt, but they are not active [N24] |
| `composite_assay` | `composite` | `assay` | config-only [N24] | yes [N24] | composite runtime | merged Silver/Gold | composite contract surface | config only [N24] | excluded | current `main` is ChEMBL-only enrichment [N24] |

## 4. Fact Base

| Area | Provider | Pipeline | Artifact | Факт | Вывод |
|---|---|---|---|---|---|
| Registry coverage | all non-ChEMBL | all 7 entity pipelines | `_registry_manifest_non_chembl.py` [N1] | Separate canonical manifest registers all 7 non-ChEMBL pipelines with transformer, Silver, Gold and Pandera schemas. | Structural scope complete for entity pipelines. |
| Fixture coverage | all | all 7 entity pipelines | `bronze_fixture_manifest.yaml` [N2] | Every pipeline has tracked 20-record fixture; 5 have tracked edge fixtures. | Repo has bounded observed-value evidence across whole non-ChEMBL scope, but edge confidence is uneven. |
| Contract governance | all | all 7 entity pipelines | `contract_registry.yaml` [N3] | All 7 non-ChEMBL contracts are active; `crossref.works` remains deprecated alias. | Gold governance coverage exists; one legacy alias still preserved. |
| Raw publication vocabularies | publication providers | crossref/openalex/pubmed/semanticscholar | `publication_controlled.yaml` [N4] | Raw provider type/status vocabularies are externalized separately from unified taxonomy and preserve unknown values by policy. | Publication family does not incorrectly close raw provider universes. |
| Identifier canonicalization | publication/openalex/uniprot/pubchem | multiple | `reference_ids.py` [N5] | Canonical families exist for DOI, PMID, PMCID, ISSN, ORCID, ROR, OpenAlex IDs, UniProt, GO, InterPro, Pfam, Reactome, PDB, DrugBank, ChEMBL. | Cross-provider identifier normalization is already centralized and domain-pure. |
| Structured payload governance | publication + uniprot | multiple | `structured_payload_policies.py` [N6] | Semantic-sensitive payloads explicitly require raw JSON sidecars plus canonical JSON. | Raw/canonical dual-field strategy is formalized, not accidental. |
| Publication structured-field governance | publication providers | multiple | `publication_structured_fields.py` [N7] | Publication structured fields declare collection semantics, representation, identifier families and hash ordering. | Publication JSON-like surfaces already have an explicit governance inventory. |
| PubMed normalization | pubmed | `pubmed_publication` | config/profile/transformer/tests [N8] | `publication_status` is strict enum, DOI/PMID canonicalize, publication types remain raw/open-world, structured affiliations have raw/canonical sidecars. | PubMed is semantically rich and mostly well-governed. |
| CrossRef normalization | crossref | `crossref_publication` | config/profile/transformer/tests [N9] | DOI canonicalization and unified publication taxonomy exist; `publication_type` remains raw provider value; structured fields exist but have weaker sidecar policy than other providers. | CrossRef is functionally aligned but less explicit for structured semantics. |
| OpenAlex normalization | openalex | `openalex_publication` | config/profile/transformer/tests [N10] | `openalex_id`, DOI, ORCID, ROR, topic IDs and OA status are canonicalized; `primary_topic` and `grants` use raw/canonical sidecars. | OpenAlex has the strongest publication-side structured semantic governance. |
| Semantic Scholar normalization | semanticscholar | `semanticscholar_publication` | config/profile/transformer/tests [N11] | S2 paper/author IDs, DOI and OA status normalize; `publication_type` remains open-world; multiple structured payloads use raw/canonical sidecars. | Strong structured governance, but provider raw types are intentionally not closed. |
| PubChem normalization | pubchem | `pubchem_compound` | config/profile/transformer/tests [N12] | Explicit normalization centers on molecule ID, SMILES, and `chemical_standardization_*`; many remaining fields are generic scalar surfaces. | PubChem family has thinner semantic normalization than publications and UniProt. |
| UniProt protein normalization | uniprot | `uniprot_protein` | config/profile/transformer/tests [N13] | Strong canonicalization for accessions, xrefs and taxonomy; structured `features_json` has governed raw/canonical sidecars; nested semantic vocabulary registry exists. | UniProt protein is strong on identifiers, medium on deep nested vocabularies. |
| UniProt idmapping normalization | uniprot | `uniprot_idmapping` | config/profile/transformer/tests [N14] | `target_id`, `uniprot_accession`, `all_mappings` and `mapping_status` are explicit normalization surfaces; conditional DQ enforces found→accession link. | Composite bridge anchor governance is explicit and testable. |
| Composite publication boundary | composite | `composite_publication` | config/tests [N15] | Primary join keys are canonical `doi` and `pmid`; title is trimmed fallback; harmonized publication taxonomy is promoted in merge config. | Non-ChEMBL publication normalization directly affects joins and merge semantics. |
| Composite molecule boundary | composite | `composite_molecule` | config/tests [N16] | Active join keys use canonical `inchi_key` and `canonical_smiles`; PubChem normalized anchors are retained but not activated as symmetric join keys. | Composite preserves PubChem provider-specific anchors without over-trusting them as join keys. |
| Composite target boundary | composite | `composite_target` | config/tests [N17] | UniProt protein dependency is gated by normalized `uniprot_accession` and `mapping_status='found'`. | ID mapping normalization is a hard join boundary, not a soft decoration. |
| Observed-value governance | all | all 7 entity pipelines | `non_chembl_observed_values.yaml` + cross-layer contract test [N18] | Repo already stores observed raw values, expected normalized values, controlled vocab sets and structured shape policies for non-ChEMBL pipelines. | A unified evidence surface already exists and can be extended rather than invented from scratch. |

## 5. Unified Enum / Vocabulary Inventory

| Provider | Pipeline | Field | Layer | Observed values/examples | Cardinality | Classification | Current normalization | Proposed normalization | Priority |
|---|---|---|---|---|---:|---|---|---|---|
| PubMed | `pubmed_publication` | `publication_status` | Silver/Gold/DQ/Contract | `ppublish`, `epublish`, `aheadofprint` [N8][N18] | 3 | strict enum | config enum + profile governed vocabulary with `preserve_unknown=True` [N8] | keep strict, add explicit publication lifecycle docs in inventory docs | P1 |
| PubMed | `pubmed_publication` | `publication_type` | Silver | `Journal Article`, `Review`, `Future PubMed Type` [N8][N18] | open-world | raw provider value / controlled vocabulary | raw preserved; unified taxonomy derived separately [N4][N8] | keep open-world raw + derived taxonomy; do not close | P1 |
| PubMed | `pubmed_publication` | `publication_types` | Silver/Gold | `Journal Article`, `Review`, `Clinical Trial`, `Meta-Analysis` in edge fixture [N18] | bounded sample | controlled vocabulary evidence set | canonical JSON string; set-like; raw sidecar=`publication_type` [N7][N8] | keep raw array evidence + optional reviewed observed registry expansion | P2 |
| CrossRef | `crossref_publication` | `publication_type` | Silver | `journal-article`, `book-chapter`, `posted-content`, `future-provider-type` [N9][N18] | open-world | raw provider value | governed raw publication vocab with preserve-unknown [N4][N9] | keep raw; avoid enum-closing; strengthen docs/tests around type families | P1 |
| OpenAlex | `openalex_publication` | `publication_type` | Silver | `article`, `review`, `book-chapter` [N10][N18] | provider-expandable | raw provider value | governed raw publication vocab with preserve-unknown [N4][N10] | keep raw + derived taxonomy | P1 |
| OpenAlex | `openalex_publication` | `type_crossref` | Silver | `journal-article`, `future-crossref-type` [N10][N18] | provider-expandable | raw provider sidecar | raw sidecar preserved; inherits CrossRef vocabulary family [N4][N10] | keep sidecar explicit; add composite/no-coalesce guidance | P1 |
| OpenAlex | `openalex_publication` | `oa_status` | Silver/Gold/DQ | `gold`,`green`,`hybrid`,`bronze`,`closed` [N10][N18] | 5 | strict enum | shared OA status normalizer + DQ conditions on unified type fields [N10] | keep strict; surface source registry in generated matrix/docs | P1 |
| Semantic Scholar | `semanticscholar_publication` | `publication_type` | Silver | `JournalArticle`, `Review`, `FutureSemanticScholarType` [N11][N18] | open-world | raw provider value | known provider spellings canonicalized; unknown preserved [N11] | keep open-world; expand registry/tests for known aliases | P1 |
| Semantic Scholar | `semanticscholar_publication` | `publication_types` | Silver/Gold | `JournalArticle`, `Review`, `ClinicalTrial` in edge fixture [N18] | bounded sample | controlled vocabulary evidence set | canonical JSON string + raw sidecar + unordered-set policy [N6][N11] | keep as derived evidence set, not strict enum | P1 |
| Semantic Scholar | `semanticscholar_publication` | `oa_status` | Silver/Gold | `gold`,`green`,`hybrid`,`bronze`,`closed` plus unknown case test [N11][N18] | 5 + unknown seam | strict enum | shared OA registry; unknown fail-closed to null [N11][N18] | keep strict; document null-on-unknown semantics explicitly | P1 |
| OpenAlex/PubMed/CrossRef/S2 | publication family | `publication_type_unified` | Silver/Gold/DQ/Composite | `article`, `review`, `book_chapter`, etc. [N18] | taxonomy-backed | derived vocabulary | shared classification rules from raw provider type [N8][N9][N10][N11] | keep strict derived taxonomy; expand provider mapping tests | P1 |
| PubChem | `pubchem_compound` | `chemical_standardization_status` | Silver/Gold/DQ | `standardized`,`partial`,`invalid`,`missing_structure` [N12][N18] | 4 | strict enum | contract constant + config DQ + profile enum [N12] | keep strict | P1 |
| PubChem | `pubchem_compound` | `chemical_standardization_policy_version` | Silver/Gold/DQ | `pubchem-basic-v1` [N12][N18] | 1 | strict enum | singleton contract value [N12] | keep strict singleton | P1 |
| UniProt | `uniprot_protein` | `entry_type` | Silver/Gold/DQ | `UniProtKB reviewed (Swiss-Prot)`, `UniProtKB unreviewed (TrEMBL)` [N13][N18] | 2 | strict enum | config enum + profile enum [N13] | keep strict | P1 |
| UniProt | `uniprot_protein` | `flag` | Silver/Gold/DQ | `Fragment`,`Precursor`,`Fragments` [N13][N18] | 3 | strict enum / flag-like status | config enum + profile enum [N13] | keep strict; document semantic difference between `Fragment` and `Fragments` | P2 |
| UniProt | `uniprot_protein` | `protein_existence` | Silver/Gold/DQ | 3 observed of provider vocabulary [N13][N18] | provider vocabulary | controlled vocabulary behaving as strict enum in project | config enum + profile enum [N13] | keep strict project registry; periodically reconcile with provider docs/VCR | P1 |
| UniProt | `uniprot_idmapping` | `mapping_status` | Silver/Gold/DQ/Composite | `found`,`not_found`,`error`,`multiple` [N14][N18] | 4 | strict enum | config enum + profile enum + composite gate [N14][N17] | keep strict | P1 |
| UniProt | `uniprot_idmapping` | `reviewed` | Silver/Gold | `true`,`false` [N14][N18] | 2 | boolean-like | boolean coercion + gold filter on `uniprot_protein.reviewed` [N13][N17] | keep strict boolean | P2 |
| OpenAlex | `openalex_publication` | `primary_topic` | Silver/Gold/Composite | topic object with OpenAlex topic ID [N10][N18] | structured object | ontology/reference-backed structured payload | canonical JSON object + raw sidecar + topic ID canonicalization [N6][N10] | keep dual-field strategy; add dedicated topic observed-inventory growth | P1 |
| PubMed | `pubmed_publication` | `subject_mesh` | Silver/Gold/Composite | MeSH labels from fixtures [N8][N18] | provider vocabulary | controlled vocabulary / ontology-backed labels | canonical JSON/set-like list, but no separate MeSH descriptor/qualifier entity pipeline | keep raw labels; add descriptor/qualifier canonical ID extraction only if downstream needs it | P2 |
| UniProt | `uniprot_protein` | nested `feature_types` | inside `features_json` | `Active site`, `Binding site`, `Domain`, `Modified residue` [N6][N13] | reviewed observed set | controlled vocabulary inside structured payload | registry `uniprot_semantic_payloads.yaml` governs nested term families [N6][N13] | expand nested vocabulary governance to more feature/comment families | P1 |

## 6. Identifier Canonicalization Inventory

| Identifier family | Providers/pipelines | Fields | Current canonicalization | Issues | Proposed canonicalization | Hash impact | Contract impact |
|---|---|---|---|---|---|---|---|
| DOI | publication family | `doi` | lowercased bare DOI via shared reference normalizer; cross-provider parity test exists [N5][N18][N25] | none structural; title fallback still needed when DOI missing | keep shared seam; add VCR-backed provider drift checks | high join/hash relevance | none if unchanged |
| PMID | PubMed/OpenAlex/S2/composite | `pmid` | digits-only canonical text via shared normalizer and DQ parity test [N5][N18][N25] | CrossRef lacks PMID surface; composite title fallback still asymmetrical | keep shared seam; extend composite docs/tests | high composite join relevance | none if unchanged |
| PMCID | publication family | `pmc_id` | canonical `PMC...` in registry [N5] | not consistently surfaced across providers; often null | keep optional canonical ID, no enum semantics | low | none |
| ISSN | CrossRef/OpenAlex/PubMed | `issn`, `issn_list`, `issn_print`, `issn_electronic` | canonical `1234-567X` via shared normalizer [N5][N8][N9][N10] | Cross-provider source preference differs; CrossRef has richest variants | keep shared seam; add publication-source merge note | medium | none |
| ORCID | publication family | `author_orcids` | canonical hyphenated ORCID IDs [N5][N8][N9][N10][N11] | only arrays, not richer author entity | keep as identifier array; no enumization | medium | none |
| ROR | OpenAlex | `ror_ids` | canonical `https://ror.org/...` URLs [N5][N10] | publication composite does not yet exploit for institutional joins | keep canonical URLs; consider derived institution dimension later | medium | additive if promoted downstream |
| OpenAlex work/author/topic IDs | OpenAlex | `openalex_id`, `author_openalex_ids`, `primary_topic` | stripped canonical `W...`, `A...`, `T...` IDs [N5][N10][N18] | topic objects only partially externalized | keep shared seam; expand topic-specific tests | medium | none if stable |
| Semantic Scholar IDs | Semantic Scholar | `paper_id`, `author_s2_ids` | lowercase stable hex IDs [N5][N11][N18] | mixed legacy/non-hex IDs would remain raw | keep preserve-unknown behavior for non-hex | medium | none |
| PubChem CID | PubChem | `molecule_id` | `CID:2244` -> `2244` [N12][N18] | only CID family governed; SID/AID not present in current pipeline | keep CID canonicalization; add policy if SID/AID pipelines appear | high for composite molecule lineage | none |
| UniProt accession | UniProt family | `accession`, `secondary_accessions`, `uniprot_accession`, `all_mappings` | uppercase canonical accession [N5][N13][N14][N18] | `all_mappings` is mixed family, not typed per item | keep canonicalization; consider typed structured payload for mixed mappings | high in composite target | possible additive sidecar |
| GO / InterPro / Pfam / Reactome / PDB | UniProt protein | `go_terms`, `interpro_xrefs`, `pfam_xrefs`, `reactome_xrefs`, `pdb_xrefs` | family-specific canonicalizers in shared registry [N5][N13][N18] | deep nested semantics still provider-local | keep shared seam; expand downstream ontology docs | medium | none |
| ChEMBL target IDs inside non-ChEMBL | UniProt idmapping | `target_id`, `all_mappings` | uppercase canonical `CHEMBL...` [N5][N14][N18] | mixed identifier set semantics in `all_mappings` | keep canonicalization; consider split arrays by family | medium | additive if changed |
| NCBI taxonomy | UniProt | `taxonomy_id` | digits-only canonical text [N5][N13][N14][N18] | `uniprot_protein` has no tracked edge fixture for taxonomy variants | keep seam; add edge fixture | medium | none |
| MeSH descriptor IDs | publication family potential | none explicit in current entity rows | registry exists for canonical `mesh` IDs [N5] | PubMed/OpenAlex currently keep label-like `subject_mesh`, not canonical descriptor/qualifier IDs | add explicit canonical ID extraction only if composite/reference use appears | high if added later | would be additive/breaking depending field choice |

## 7. JSON / Structured Field Inventory

| Provider | Pipeline | Field | Shape | Current representation | Current serialization | Deterministic? | Contract type | Proposed representation | Priority |
|---|---|---|---|---|---|---|---|---|---|
| PubMed | `pubmed_publication` | `authors_with_affiliations` | ordered author-affiliation objects | canonical JSON string + raw sidecar | sidecar pair with ordered semantics [N6][N8][N18] | yes for hash/order policy | string | keep as-is | P1 |
| PubMed | `pubmed_publication` | `affiliation_structured` | affiliation objects | canonical JSON string + raw sidecar | unordered-set semantics [N6][N8][N18] | yes | string | keep as-is | P1 |
| CrossRef | `crossref_publication` | `references` | list of reference objects | canonical JSON string only | generic JSON serialization via transformer [N9] | partially governed | string | add explicit structured payload policy if downstream semantic transforms are planned | P1 |
| CrossRef | `crossref_publication` | `author_details` | list of author objects | canonical JSON string only | generic JSON serialization [N9] | partially governed | string | consider raw sidecar only if semantic extraction expands | P2 |
| OpenAlex | `openalex_publication` | `grants` | list of grant objects | canonical JSON string + raw sidecar | unordered-set policy [N6][N10][N18] | yes | string | keep as-is | P1 |
| OpenAlex | `openalex_publication` | `primary_topic` | structured topic object | canonical JSON string + raw sidecar | structured-object policy [N6][N10][N18] | yes | string | keep as-is | P1 |
| OpenAlex | `openalex_publication` | `subject_topics` | list of topic objects | canonical JSON string | topic-ID canonicalization [N10] | mostly | string | add explicit sidecar policy if topic semantics expand | P2 |
| Semantic Scholar | `semanticscholar_publication` | `publication_types` | list of provider type labels | canonical JSON string + raw sidecar | unordered-set policy [N6][N11][N18] | hash yes; payload equality not forced by golden test [N25] | string | keep dual-field; consider canonical list sorting for persisted payload too | P1 |
| Semantic Scholar | `semanticscholar_publication` | `subject_fields` | list of subject labels | canonical JSON string + raw sidecar | unordered-set policy [N6][N11][N18] | yes | string | keep as-is | P1 |
| Semantic Scholar | `semanticscholar_publication` | `citation_contexts` | ordered citation snippets | canonical JSON string + raw sidecar | ordered-sequence policy [N6][N11][N18] | yes | string | keep as-is | P1 |
| Semantic Scholar | `semanticscholar_publication` | `author_h_indices` | ordered numeric list aligned with authors | canonical JSON string + raw sidecar | ordered-sequence policy [N6][N11][N18] | yes | string | keep as-is | P1 |
| UniProt | `uniprot_protein` | `features_json` | ordered feature objects | canonical JSON string + raw sidecar | semantic-sensitive policy + nested vocab registry [N6][N13][N18] | yes | string | keep as-is; expand governed nested vocab families | P1 |
| UniProt | `uniprot_protein` | `lineage`, `isoform_ids`, `protein_alternative_names`, `reactions` | lists | canonical JSON string | set-like or ordered depending field/profile [N13] | mostly | string | extend explicit policy inventory beyond `features_json` for highest-risk fields | P2 |
| UniProt | `uniprot_idmapping` | `all_mappings` | mixed identifier list | canonical JSON string | unordered-set normalization [N14][N18] | yes | string | consider typed object array if downstream needs family-specific semantics | P1 |

## 8. Reuse / Drift Matrix

| Rule / Field Family | Providers/pipelines using it | Implemented where | Is behavior identical? | Drift risk | Recommendation |
|---|---|---|---|---|---|
| DOI canonicalization | all publication providers + composite publication | `reference_ids.py`, transformers, cross-provider test [N5][N25] | yes | low | keep shared seam |
| PMID canonicalization | PubMed, OpenAlex, Semantic Scholar, composite publication | `reference_ids.py`, entity configs, DQ parity test [N5][N18][N25] | yes | low | keep shared seam |
| Raw publication type open-world policy | CrossRef, OpenAlex, PubMed, Semantic Scholar | `publication_controlled.yaml`, profiles, observed inventory [N4][N18] | mostly yes | medium | add one generated parity gate comparing config/profile/matrix to raw vocab registry |
| Derived publication taxonomy | publication family + composite publication | `_publication_classification_rules.py`, entity configs, composite config [N8][N9][N10][N11][N15] | yes | low | keep strict derived taxonomy |
| OA status normalization | OpenAlex, Semantic Scholar | shared value normalizer + configs/tests [N10][N11][N18] | yes for known values, fail-closed on unknown in S2 tests | medium | document unknown semantics explicitly and add same matrix row language across providers |
| ORCID / ISSN canonical arrays | publication family | shared identifier registry + publication structured field registry [N5][N7] | yes | low | keep |
| Structured payload raw/canonical sidecars | PubMed, OpenAlex, Semantic Scholar, UniProt | `structured_payload_policies.py` [N6] | no: CrossRef largely absent | medium | decide whether CrossRef stays intentionally flat or gets equivalent sidecar policy for selected fields |
| PubChem scalar property normalization | PubChem only | generic float/int/text normalizers + entity DQ config [N12] | entity-specific only | medium | add explicit provider semantic registry for highest-risk property/status/unit families |
| UniProt nested semantic vocabularies | UniProt protein only | `uniprot_semantic_payloads.yaml` + features policy [N6][N13] | partial | medium | expand to more comment/feature/xref families |
| Composite join-key normalization | publication, molecule, target composites | composite configs + boundary tests [N15][N16][N17] | yes | low | keep and add more edge fixtures for title/smiles/accession variants |
| Mixed identifier sets | `uniprot_idmapping.all_mappings` | profile + observed inventory [N14][N18] | unique to pipeline | high | decide whether mixed family remains acceptable or should become typed payload |

## 9. Gap Analysis

### missing normalization

- No current P0 “missing normalization” blocker was confirmed for any registered non-ChEMBL entity pipeline [N1][N18].
- The weakest normalization breadth is `pubchem_compound`, where semantic handling is much thinner than in publication and UniProt families [N12].

### weak canonicalization

- `crossref_publication` has structured payloads but lacks the explicit raw/canonical sidecar policy used by PubMed/OpenAlex/Semantic Scholar for semantic-sensitive fields like `references` and `author_details` [N6][N9].
- `uniprot_protein` strongly canonicalizes identifiers, but many structured fields besides `features_json` remain outside explicit semantic-payload governance [N6][N13].

### missing enum externalization

- Publication raw vocabularies are already externalized [N4].
- PubChem and UniProt still rely more on inline config/profile enums and less on family-level reviewed vocab registries outside their narrow status families [N12][N13][N14].

### missing vocabulary registry

- No reviewed registry exists for broader UniProt nested semantic surfaces beyond `feature_types`, `comment_types`, `keyword_categories` [N13].
- No family-level registry yet governs higher-order PubChem property/status/category semantics beyond chemical standardization [N12].

### schema / contract mismatch

- No active entity-pipeline coverage gap in registry/config/schema/contract chain was found [N1][N3][N18].
- One legacy contract alias `crossref.works` remains deprecated but present; this is governance noise, not a current mismatch [N3].

### hashing inconsistency

- Hash stability is explicitly tested across non-ChEMBL profiles, including meta-field exclusion [N25].
- For some unordered semantic payloads, hash equality is enforced even when normalized payload equality is not asserted, which means hash policy can be stronger than persisted canonical representation. This is acceptable today but should be made explicit in docs/matrix for governed unordered payloads [N25].

### DQ mismatch

- Publication-family DQ intentionally validates derived taxonomy fields more strongly than raw provider type fields [N9][N10][N17][N18]. This is good, but only if docs/matrix keep stating that raw types remain open-world.
- PubChem and UniProt rely more on config-enum + profile alignment than on external reviewed registries for some status families [N12][N13][N14].

### identifier canonicalization mismatch

- No structural mismatch found for DOI/PMID/ISSN/ORCID/OpenAlex/UniProt core IDs [N5][N18][N25].
- `all_mappings` in `uniprot_idmapping` is intentionally mixed-family and therefore semantically weaker than typed arrays [N14][N18].

### ontology/reference handling mismatch

- Strong for UniProt xrefs and OpenAlex topic IDs through shared registry [N5][N10][N13].
- Weaker for PubMed/OpenAlex MeSH-like topic/mesh label surfaces, which remain label-level rather than canonical descriptor/qualifier ID surfaces [N8][N10][N18].

### JSON canonicalization mismatch

- Publication and UniProt already use ADR-035 canonical JSON string policy with explicit governance registries [N6][N7][N20].
- CrossRef still exposes structured fields without the same raw-sidecar rigor as the other publication providers [N6][N9].

### architectural placement issue

- No evidence of filesystem/config parsing inside domain normalization profiles was found for non-ChEMBL rules. Shared registries are immutable and domain-pure [N4][N5][N6][N7].

### cross-provider normalization drift

- Publication family is mostly aligned on canonical identifiers and derived taxonomy, but still heterogeneous on structured payload policy depth and raw-sidecar use [N6][N8][N9][N10][N11].
- PubChem and UniProt are not yet part of a wider shared “non-ChEMBL semantic registry” beyond identifiers and some status fields [N12][N13][N14].

### composite merge normalization mismatch

- `composite_publication` title fallback remains intentionally weaker than DOI/PMID joins and therefore more vulnerable to formatting drift or provider title divergence [N15][N17].
- `composite_target` depends on normalized idmapping gate; any future change to `mapping_status` or accession normalization is composite-breaking [N14][N17].

### fixture / VCR / sample coverage gap

- Edge fixture manifest coverage is absent for `crossref_publication` and `uniprot_protein` [N2][N18].
- VCR coverage exists for all provider families, so the gap is specifically in tracked Bronze edge-fixture governance rather than in HTTP replay evidence [N23].

### replay / debug traceability gap

- No direct normalization-specific replay blocker was found. The project-level determinism and canonical JSON rules already anchor replay/debug semantics [N20][N21][N22].
- The main residual gap is governance depth: if normalization rules expand for PubChem or UniProt nested payloads, observed-value and golden-hash inventories must evolve in lockstep [N18][N25].

## 10. Proposed Normalization Extensions

| Extension | Layer placement | Expected input/output | Affected providers/pipelines | Backward compatibility | `content_hash` impact | Silver/Gold contract impact | DQ impact | Composite impact | Derived/reference impact | Migration/backfill needs | Required tests | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Generated parity gate: raw publication vocab registry vs matrix/config/profile | tests/config + docs matrix | input: `publication_controlled.yaml`, entity configs, generated matrix; output: equality/subset report | CrossRef/OpenAlex/PubMed/S2 | non-breaking | none | none | prevents future raw-type drift | keeps publication merge semantics explainable | none | none | config + matrix tests | P1 |
| Explicit CrossRef structured payload policy for `references` and `author_details` if semantic transforms are expected | domain normalization registry + config/tests | raw JSON + canonical JSON sidecars | `crossref_publication` | additive | possible if persisted fields added to hash or exclusion list | additive columns if sidecars added | clearer typing and policy | safer publication composite semantics | can seed future reference/author dimensions | maybe if new persisted sidecars added | unit policy tests + contract/matrix tests | P1 |
| UniProt nested semantic payload registry expansion | `configs/vocab/uniprot_semantic_payloads.yaml` + profile tests | nested feature/comment/xref term families | `uniprot_protein` | non-breaking if registry-only; potentially breaking if normalization starts coercing nested values | medium if canonical payload changes | maybe none if envelope unchanged | stronger nested vocabulary checks | improves composite target explainability | stronger downstream protein feature dims | maybe if canonical payload content changes | nested vocabulary tests + golden hash review | P1 |
| PubChem semantic registry for reviewed property/status/unit families | `configs/vocab/pubchem_controlled.yaml` + profile/config parity tests | reviewed controlled terms for structural/property metadata | `pubchem_compound` | likely non-breaking if observational first | medium where canonicalized fields change | possible contract note only at first | stronger DQ semantics | improves composite molecule interpretability | could seed future chemical-reference dimensions | only if canonicalization starts changing existing values | config parity + golden hash tests | P1 |
| Edge Bronze fixtures for `crossref_publication` and `uniprot_protein` | fixtures + manifest + normalization tests | edge JSONL samples for rare type/status/identifier cases | CrossRef, UniProt Protein | non-breaking | none | none | stronger observed-value evidence | improves composite regression confidence | none | none | fixture manifest + edge observed-value tests | P1 |
| Typed strategy for `uniprot_idmapping.all_mappings` | profile + config + maybe sidecar contract | raw mixed list -> canonical mixed list or typed object array | `uniprot_idmapping`, `composite_target` | potentially breaking if field representation changes | medium/high | contract-sensitive | could separate DQ per identifier family | clearer target bridge semantics | could seed mapping dimension pipeline later | likely yes if representation changes | contract + composite boundary + golden hash tests | P1 |
| Publication title fallback hardening | composite join-key layer | input title variants -> canonical join fallback | `composite_publication` | potentially behavior-changing | none unless persisted normalized title added | maybe additive sidecar only | none | reduces null enrichment on missing DOI/PMID | none | maybe not | join-key normalization tests + VCR-backed cases | P2 |
| Observed-value inventory enrichment from VCRs | scripts/docs/tests | Bronze + VCR observed set snapshots | all non-ChEMBL pipelines | non-breaking | none | none | improves reviewed vocab evidence | better composite confidence | can reveal candidate derived dimensions | none | inventory generation tests | P2 |

## 11. P0–P2 Plan

### P0

Current `main` does not show a confirmed P0 blocker in non-ChEMBL normalization. No immediate defect equivalent to “missing canonicalization” or “broken contract chain” was confirmed [N1][N3][N18].

### P1

1. Add parity gate for raw publication vocabularies vs profiles/configs/generated matrix [N4][N18].
2. Add tracked edge Bronze fixtures for `crossref_publication` and `uniprot_protein` [N2][N18].
3. Expand UniProt nested semantic payload registry beyond the current `features_json` reviewed families [N6][N13].
4. Introduce explicit PubChem reviewed semantic registry for property/status/unit families beyond `chemical_standardization_*` [N12].
5. Decide whether `crossref_publication` should gain raw/canonical sidecar governance for `references` and `author_details`, or whether current flat treatment is intentional and final [N6][N9].
6. Decide whether `uniprot_idmapping.all_mappings` remains a mixed identifier set or should be promoted to typed mixed-reference payload [N14][N18].

### P2

1. Grow observed-value inventory using VCR cassette replay artifacts, not just tracked Bronze fixtures [N23].
2. Tighten docs/matrix language around unordered semantic payloads where hash determinism is stricter than payload-equality guarantees [N25].
3. Consider title-fallback normalization hardening for `composite_publication`, but only after preserving source-title semantics and documenting false-positive join risk [N15].

## 12. Architectural Verdict

### Layer correctness

Pass.

The current non-ChEMBL normalization stack stays within Hexagonal / domain-pure boundaries:
shared vocabularies and identifier registries are immutable domain artifacts, not filesystem-parsing logic inside domain profiles [N4][N5][N6][N7][N22].

### Determinism

Mostly pass.

Canonical identifier seams, canonical JSON string policy and golden hash tests already enforce deterministic behavior for the highest-risk non-ChEMBL surfaces [N20][N21][N25]. The remaining work is to expand governance depth, not to re-architect determinism.

### Medallion correctness

Mostly pass.

Bronze tracked fixtures remain raw evidence; Silver is where normalization occurs; Gold contracts are active and cross-layer coverage is tested for non-ChEMBL surfaces [N2][N3][N18][N20][N22].

### Composite correctness

Pass with P1 hardening.

Current non-ChEMBL composites already document and test their normalized join boundaries:
publication uses canonical DOI/PMID, molecule uses InChIKey/SMILES with bounded PubChem anchors, target gates UniProt enrichment through normalized ID mapping [N15][N16][N17].

The main remaining risk is governance drift, not missing composite normalization.

## 13. Sources

- [N1] `src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py`
- [N2] `configs/base/bronze_fixture_manifest.yaml`
- [N3] `configs/base/contract_registry.yaml`
- [N4] `configs/vocab/publication_controlled.yaml`
- [N5] `src/bioetl/domain/normalization/reference_ids.py`
- [N6] `src/bioetl/domain/normalization/structured_payload_policies.py`
- [N7] `src/bioetl/domain/normalization/publication_structured_fields.py`
- [N8] `configs/entities/pubmed/publication.yaml`; `src/bioetl/domain/normalization/profiles/pubmed_publication.py`; `src/bioetl/application/pipelines/pubmed/transformer.py`; `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
- [N9] `configs/entities/crossref/publication.yaml`; `src/bioetl/domain/normalization/profiles/crossref_publication.py`; `src/bioetl/application/pipelines/crossref/transformer.py`
- [N10] `configs/entities/openalex/publication.yaml`; `src/bioetl/domain/normalization/profiles/openalex_publication.py`; `src/bioetl/application/pipelines/openalex/transformer.py`
- [N11] `configs/entities/semanticscholar/publication.yaml`; `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`; `src/bioetl/application/pipelines/semanticscholar/transformer.py`
- [N12] `configs/entities/pubchem/compound.yaml`; `src/bioetl/domain/normalization/profiles/pubchem_compound.py`; `src/bioetl/application/pipelines/pubchem/transformer.py`; `src/bioetl/domain/normalization/chemical_standardization_contract.py`
- [N13] `configs/entities/uniprot/protein.yaml`; `src/bioetl/domain/normalization/profiles/uniprot_protein.py`; `src/bioetl/application/pipelines/uniprot/transformer.py`; `configs/vocab/uniprot_semantic_payloads.yaml`
- [N14] `configs/entities/uniprot/idmapping.yaml`; `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`; `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py`
- [N15] `configs/composites/publication.yaml`; `tests/unit/config/test_non_chembl_composite_boundary_policy.py`; `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`
- [N16] `configs/composites/molecule.yaml`; `tests/unit/config/test_non_chembl_composite_boundary_policy.py`; `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`
- [N17] `configs/composites/target.yaml`; `tests/unit/config/test_non_chembl_composite_boundary_policy.py`; `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`
- [N18] `tests/fixtures/normalization/non_chembl_observed_values.yaml`; `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`; `tests/integration/normalization/test_non_chembl_edge_observed_values.py`; `tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py`
- [N19] `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- [N20] `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`
- [N21] `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- [N22] `docs/00-project/RULES.md`
- [N23] `tests/fixtures/vcr/{crossref,openalex,pubchem,pubmed,semanticscholar,uniprot}/...`; `tests/contract/_provider_contract_replay.py`
- [N24] `configs/composites/activity.yaml`; `configs/composites/assay.yaml`
- [N25] `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`; `tests/integration/test_cross_provider_doi_normalization.py`; `tests/architecture/test_non_chembl_json_field_typing_policy.py`

# Publication Types by Provider

Reference of all known `publication_type` values across data providers.

Last updated: 2026-02-09

---

## 1. OpenAlex (`type` field)

Source: [Work object docs](https://docs.openalex.org/api-entities/works/work-object) |
Live enum: `GET https://api.openalex.org/works?group_by=type`

24 values (sorted by record count, Feb 2026):

| Value | Records | Description |
|---|---:|---|
| `article` | 208 763 871 | Journal articles, conference papers, posted content |
| `book-chapter` | 24 030 031 | Chapter within a book |
| `dataset` | 13 237 674 | Dataset |
| `dissertation` | 7 274 270 | Dissertation / thesis |
| `preprint` | 6 933 054 | Preprint (hosted on preprint server or flagged in metadata) |
| `book` | 5 968 196 | Book (includes former reference-book, monograph) |
| `other` | 5 566 750 | Uncategorized |
| `review` | 4 142 131 | Review article (from review-only journals) |
| `paratext` | 3 897 895 | Front-cover, TOC, masthead, journal itself |
| `libguides` | 1 776 332 | Library guide |
| `letter` | 1 721 092 | Letter |
| `report` | 951 401 | Report |
| `reference-entry` | 904 552 | Entry in a reference book |
| `peer-review` | 882 106 | Peer review |
| `editorial` | 786 237 | Editorial |
| `erratum` | 419 313 | Correction / erratum |
| `standard` | 411 035 | Standard |
| `supplementary-materials` | 66 369 | Supplementary materials |
| `retraction` | 23 134 | Retraction notice |
| `software` | 1 517 | Software |
| `database` | 1 034 | Database |
| `book-section` | 734 | Book section |
| `report-component` | 378 | Report component |
| `grant` | 102 | Grant |

> **Notes:**
> - `type_crossref` field preserves the original CrossRef type for backward compatibility.
> - OpenAlex reclassified ~4 M works from `article` to `editorial`, `erratum`, `letter`, `preprint`, `review`, `retraction` using PubMed data (Jul 2024).
> - `book` merges former `book`, `reference-book`, `monograph`.
> - Use `group_by=type:include_unknown` to include records with no type.

---

## 2. CrossRef (`type` field)

Source: `GET https://api.crossref.org/types` (30 values, Feb 2026)

| Value | Description |
|---|---|
| `journal-article` | Journal article |
| `book-chapter` | Chapter within a book |
| `proceedings-article` | Conference proceedings article |
| `book` | A complete book |
| `dataset` | Dataset |
| `report` | Report |
| `standard` | Standard |
| `peer-review` | Peer review |
| `component` | Component (figure, table, supplement) |
| `posted-content` | Posted content (preprints, working papers) |
| `monograph` | Monograph |
| `reference-entry` | Entry in a reference book |
| `dissertation` | Dissertation / thesis |
| `other` | Other / uncategorized |
| `journal-issue` | Journal issue |
| `journal` | Journal title |
| `reference-book` | Reference book |
| `book-series` | Book series |
| `edited-book` | Edited book |
| `book-set` | Set of books |
| `book-part` | Part of a book |
| `book-section` | Section of a book |
| `book-track` | Track within a book |
| `proceedings` | Conference proceedings |
| `proceedings-series` | Proceedings series |
| `report-series` | Report series |
| `report-component` | Report component |
| `grant` | Grant |
| `journal-volume` | Journal volume |
| `database` | Database |

> **Notes:**
> - Live authoritative list: `GET https://api.crossref.org/types`
> - `posted-content` covers preprints, eprints, working papers, reports, dissertations, and other informally posted content.
> - In the current codebase (`crossref/work.py`), 29 of these 30 types are listed (missing `database`).

---

## 3. PubMed (Publication Type — MeSH Category V)

Source: [NLM Publication Characteristics with Scope Notes](https://www.nlm.nih.gov/mesh/pubtypes.html)

PubMed uses a MeSH-based controlled vocabulary with **187 publication types** (as of MeSH 2025).
Below is the full list. Values are stored in `<PublicationTypeList>` XML elements.

<details>
<summary>Full list (187 types, click to expand)</summary>

| # | Publication Type |
|--:|---|
| 1 | Abbreviations |
| 2 | Abstracts |
| 3 | Academic Dissertation |
| 4 | Account Book |
| 5 | Adaptive Clinical Trial |
| 6 | Address |
| 7 | Advertisement |
| 8 | Almanac |
| 9 | Anecdotes |
| 10 | Animation |
| 11 | Annual Report |
| 12 | Aphorisms and Proverbs |
| 13 | Architectural Drawing |
| 14 | Atlas |
| 15 | Autobiography |
| 16 | Bibliography |
| 17 | Biobibliography |
| 18 | Biography |
| 19 | Blog |
| 20 | Book Illustrations |
| 21 | Book Review |
| 22 | Bookplate |
| 23 | Broadside |
| 24 | Calendar |
| 25 | Caricature |
| 26 | Cartoon |
| 27 | Case Reports |
| 28 | Catalog |
| 29 | Catalog, Bookseller |
| 30 | Catalog, Commercial |
| 31 | Catalog, Drug |
| 32 | Catalog, Publisher |
| 33 | Catalog, Union |
| 34 | Chart |
| 35 | Chronology |
| 36 | Classical Article |
| 37 | Clinical Conference |
| 38 | Clinical Study |
| 39 | Clinical Trial |
| 40 | Clinical Trial Protocol |
| 41 | Clinical Trial, Phase I |
| 42 | Clinical Trial, Phase II |
| 43 | Clinical Trial, Phase III |
| 44 | Clinical Trial, Phase IV |
| 45 | Clinical Trial, Veterinary |
| 46 | Collected Correspondence |
| 47 | Collected Work |
| 48 | Collection |
| 49 | Comment |
| 50 | Comparative Study |
| 51 | Congress |
| 52 | Consensus Development Conference |
| 53 | Consensus Development Conference, NIH |
| 54 | Controlled Clinical Trial |
| 55 | Cookbook |
| 56 | Corrected and Republished Article |
| 57 | Database |
| 58 | Dataset |
| 59 | Diary |
| 60 | Dictionary |
| 61 | Dictionary, Chemical |
| 62 | Dictionary, Classical |
| 63 | Dictionary, Dental |
| 64 | Dictionary, Medical |
| 65 | Dictionary, Pharmaceutic |
| 66 | Dictionary, Polyglot |
| 67 | Directory |
| 68 | Dispensatory |
| 69 | Documentaries and Factual Films |
| 70 | Drawing |
| 71 | Duplicate Publication |
| 72 | Editorial |
| 73 | Electronic Supplementary Materials |
| 74 | Encyclopedia |
| 75 | English Abstract |
| 76 | Ephemera |
| 77 | Equivalence Trial |
| 78 | Essay |
| 79 | Eulogy |
| 80 | Evaluation Study |
| 81 | Examination Questions |
| 82 | Exhibition |
| 83 | Expression of Concern |
| 84 | Festschrift |
| 85 | Fictional Work |
| 86 | Form |
| 87 | Formulary |
| 88 | Formulary, Dental |
| 89 | Formulary, Homeopathic |
| 90 | Formulary, Hospital |
| 91 | Funeral Sermon |
| 92 | Government Publication |
| 93 | Graphic Novel |
| 94 | Guidebook |
| 95 | Guideline |
| 96 | Handbook |
| 97 | Herbal |
| 98 | Historical Article |
| 99 | Incunabula |
| 100 | Index |
| 101 | Instructional Film and Video |
| 102 | Interactive Tutorial |
| 103 | Interview |
| 104 | Introductory Journal Article |
| 105 | Journal Article |
| 106 | Juvenile Literature |
| 107 | Laboratory Manual |
| 108 | Lecture |
| 109 | Lecture Note |
| 110 | Legal Case |
| 111 | Legislation |
| 112 | Letter |
| 113 | Manuscript |
| 114 | Manuscript, Medical |
| 115 | Map |
| 116 | Meeting Abstract |
| 117 | Meta-Analysis |
| 118 | Monograph |
| 119 | Movable Books |
| 120 | Multicenter Study |
| 121 | Network Meta-Analysis |
| 122 | News |
| 123 | Newspaper Article |
| 124 | Nurses Instruction |
| 125 | Observational Study |
| 126 | Observational Study, Veterinary |
| 127 | Outline |
| 128 | Overall |
| 129 | Patent |
| 130 | Patient Education Handout |
| 131 | Periodical |
| 132 | Periodical Index |
| 133 | Personal Narrative |
| 134 | Pharmacopoeia |
| 135 | Pharmacopoeia, Homeopathic |
| 136 | Photograph |
| 137 | Phrases |
| 138 | Pictorial Work |
| 139 | Poetry |
| 140 | Popular Work |
| 141 | Portrait |
| 142 | Postcard |
| 143 | Poster |
| 144 | Practice Guideline |
| 145 | Pragmatic Clinical Trial |
| 146 | Preprint |
| 147 | Price List |
| 148 | Problems and Exercises |
| 149 | Program |
| 150 | Programmed Instruction |
| 151 | Prospectus |
| 152 | Public Service Announcement |
| 153 | Publication Components |
| 154 | Publication Formats |
| 155 | Published Erratum |
| 156 | Randomized Controlled Trial |
| 157 | Randomized Controlled Trial, Veterinary |
| 158 | Research Support, American Recovery and Reinvestment Act |
| 159 | Research Support, N.I.H., Extramural |
| 160 | Research Support, N.I.H., Intramural |
| 161 | Research Support, Non-U.S. Gov't |
| 162 | Research Support, U.S. Gov't, Non-P.H.S. |
| 163 | Research Support, U.S. Gov't, P.H.S. |
| 164 | Research Support, U.S. Government |
| 165 | Resource Guide |
| 166 | Retracted Publication |
| 167 | Retraction of Publication |
| 168 | Review |
| 169 | Scientific Integrity Review |
| 170 | Scoping Review |
| 171 | Sermon |
| 172 | Statistics |
| 173 | Study Characteristics |
| 174 | Study Guide |
| 175 | Support of Research |
| 176 | Systematic Review |
| 177 | Tables |
| 178 | Technical Report |
| 179 | Terminology |
| 180 | Textbook |
| 181 | Twin Study |
| 182 | Unedited Footage |
| 183 | Union List |
| 184 | Unpublished Work |
| 185 | Validation Study |
| 186 | Video-Audio Media |
| 187 | Web Archive |
| 188 | Webcast |
| 189 | Wit and Humor |

</details>

### Commonly encountered PubMed publication types (biomedical research)

| Publication Type | Category |
|---|---|
| Journal Article | Research |
| Review | Research |
| Systematic Review | Research |
| Meta-Analysis | Research |
| Network Meta-Analysis | Research (new in MeSH 2025) |
| Scoping Review | Research (new in MeSH 2025) |
| Randomized Controlled Trial | Study design |
| Clinical Trial | Study design |
| Clinical Trial, Phase I–IV | Study design |
| Controlled Clinical Trial | Study design |
| Observational Study | Study design |
| Multicenter Study | Study design |
| Comparative Study | Study design |
| Validation Study | Study design |
| Case Reports | Research |
| Clinical Study | Research |
| Preprint | Format |
| Editorial | Editorial |
| Letter | Editorial |
| Comment | Editorial |
| News | Editorial |
| Published Erratum | Correction |
| Retracted Publication | Correction |
| Retraction of Publication | Correction |
| Expression of Concern | Correction |
| Practice Guideline | Guideline |
| Guideline | Guideline |
| Dataset | Data |
| Patent | IP |

> **Notes:**
> - A single PubMed record can have **multiple** publication types simultaneously.
> - `Network Meta-Analysis` and `Scoping Review` were added in MeSH 2025 with retroactive indexing.
> - `Government Publication`, `Newspaper Article`, `Overall`, `Scientific Integrity Review` are discontinued (still searchable, not applied to new records).
> - Authoritative source: [NLM Publication Types with Scope Notes](https://www.nlm.nih.gov/mesh/pubtypes.html)

---

## 4. Semantic Scholar (`publicationTypes` field)

Source: [S2 Academic Graph API](https://api.semanticscholar.org/api-docs/) |
Schema: `GET https://api.semanticscholar.org/graph/v1/swagger.json`

13 values (enum from API swagger):

| Value | Category |
|---|---|
| `JournalArticle` | Research |
| `Conference` | Research |
| `Review` | Research |
| `Study` | Research |
| `CaseReport` | Research |
| `ClinicalTrial` | Research |
| `MetaAnalysis` | Research |
| `Editorial` | Editorial |
| `LettersAndComments` | Editorial |
| `News` | Editorial |
| `Book` | Other |
| `BookSection` | Other |
| `Dataset` | Other |

> **Notes:**
> - A paper can have **multiple** publication types (JSON array), e.g., `["JournalArticle", "Review"]`.
> - Field can be `null` if no type is assigned (~37% coverage).
> - Values use PascalCase (no hyphens or spaces).

---

## 5. Cross-Provider Mapping (approximate)

| Concept | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|---|---|---|---|---|
| Journal article | `article` | `journal-article` | `Journal Article` | `JournalArticle` |
| Review | `review` | — | `Review` | `Review` |
| Systematic review | — | — | `Systematic Review` | — |
| Meta-analysis | — | — | `Meta-Analysis` | `MetaAnalysis` |
| Preprint | `preprint` | `posted-content` | `Preprint` | — |
| Book | `book` | `book` | `Monograph` | `Book` |
| Book chapter | `book-chapter` | `book-chapter` | — | `BookSection` |
| Conference paper | `article`* | `proceedings-article` | `Congress` | `Conference` |
| Dataset | `dataset` | `dataset` | `Dataset` | `Dataset` |
| Dissertation | `dissertation` | `dissertation` | `Academic Dissertation` | — |
| Editorial | `editorial` | — | `Editorial` | `Editorial` |
| Letter | `letter` | — | `Letter` | `LettersAndComments` |
| Erratum | `erratum` | — | `Published Erratum` | — |
| Retraction | `retraction` | — | `Retraction of Publication` | — |
| Report | `report` | `report` | `Technical Report` | — |
| Peer review | `peer-review` | `peer-review` | — | — |
| Standard | `standard` | `standard` | — | — |
| Patent | — | — | `Patent` | — |
| Case report | — | — | `Case Reports` | `CaseReport` |
| Clinical trial | — | — | `Clinical Trial` | `ClinicalTrial` |
| News | — | — | `News` | `News` |

\* OpenAlex conference papers have `type=article` with `primary_location.source.type=conference`.

---

## 6. Current Codebase Status

| Provider | Schema location | Validation |
|---|---|---|
| ChEMBL | `domain/schemas/constants.py` | `isin` (4 values: PUBLICATION, PATENT, DATASET, BOOK) |
| CrossRef | `domain/schemas/crossref/work.py` | `isin` (29 values) |
| OpenAlex | `domain/schemas/openalex/publication.py` | No validation (nullable=True) |
| Semantic Scholar | `domain/schemas/semanticscholar/publication.py` | No validation (nullable=True) |
| PubMed | `domain/contracts/gold/publications.py` | No validation (default "PUBLICATION") |

# Publication Types Classification: PEER / EXP / REV

Three-way classification of all known `publication_type` values:
- **PEER** — peer-review (formal evaluation of a manuscript by reviewers, published as a standalone record)
- **EXP** — original experimental data (primary research presenting new experimental results)
- **REV** — review or other citation (reviews, meta-analyses, commentary, editorial content, reference material, infrastructure)

Last updated: 2026-02-09

---

## Unified Cross-Provider Classification Table

Rows = publication type concepts. Columns = data sources.
Cells = **PEER** | **EXP** | **REV** | **—** (type absent in provider).

### PEER: Peer-Review

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 1 | Peer Review | PEER `peer-review` | PEER `peer-review` | — | — |

### EXP: Original Experimental Data

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 2 | Journal Article | EXP `article` | EXP `journal-article` | EXP `Journal Article` | EXP `JournalArticle` |
| 3 | Conference Paper | EXP `article`\* | EXP `proceedings-article` | EXP `Congress` | EXP `Conference` |
| 4 | Preprint | EXP `preprint` | EXP `posted-content` | EXP `Preprint` | — |
| 5 | Dataset | EXP `dataset` | EXP `dataset` | EXP `Dataset` | EXP `Dataset` |
| 6 | Database | EXP `database` | EXP `database` | EXP `Database` | — |
| 7 | Dissertation | EXP `dissertation` | EXP `dissertation` | EXP `Academic Dissertation` | — |
| 8 | Report | EXP `report` | EXP `report` | EXP `Technical Report` | — |
| 9 | Report Component | EXP `report-component` | EXP `report-component` | — | — |
| 10 | Component (figure/table/suppl) | — | EXP `component` | — | — |
| 11 | Supplementary Materials | EXP `supplementary-materials` | — | EXP `Electronic Supplementary Materials` | — |
| 12 | Software | EXP `software` | — | — | — |
| 13 | Patent | — | — | EXP `Patent` | — |
| 14 | Case Report | — | — | EXP `Case Reports` | EXP `CaseReport` |
| 15 | Clinical Study | — | — | EXP `Clinical Study` | EXP `Study` |
| 16 | Clinical Trial | — | — | EXP `Clinical Trial` | EXP `ClinicalTrial` |
| 17 | Clinical Trial Protocol | — | — | EXP `Clinical Trial Protocol` | — |
| 18 | Clinical Trial, Phase I | — | — | EXP `Clinical Trial, Phase I` | — |
| 19 | Clinical Trial, Phase II | — | — | EXP `Clinical Trial, Phase II` | — |
| 20 | Clinical Trial, Phase III | — | — | EXP `Clinical Trial, Phase III` | — |
| 21 | Clinical Trial, Phase IV | — | — | EXP `Clinical Trial, Phase IV` | — |
| 22 | Clinical Trial, Veterinary | — | — | EXP `Clinical Trial, Veterinary` | — |
| 23 | Adaptive Clinical Trial | — | — | EXP `Adaptive Clinical Trial` | — |
| 24 | Pragmatic Clinical Trial | — | — | EXP `Pragmatic Clinical Trial` | — |
| 25 | Equivalence Trial | — | — | EXP `Equivalence Trial` | — |
| 26 | Randomized Controlled Trial | — | — | EXP `Randomized Controlled Trial` | — |
| 27 | Randomized Controlled Trial, Vet | — | — | EXP `Randomized Controlled Trial, Veterinary` | — |
| 28 | Controlled Clinical Trial | — | — | EXP `Controlled Clinical Trial` | — |
| 29 | Observational Study | — | — | EXP `Observational Study` | — |
| 30 | Observational Study, Veterinary | — | — | EXP `Observational Study, Veterinary` | — |
| 31 | Comparative Study | — | — | EXP `Comparative Study` | — |
| 32 | Validation Study | — | — | EXP `Validation Study` | — |
| 33 | Evaluation Study | — | — | EXP `Evaluation Study` | — |
| 34 | Multicenter Study | — | — | EXP `Multicenter Study` | — |
| 35 | Twin Study | — | — | EXP `Twin Study` | — |
| 36 | Clinical Conference | — | — | EXP `Clinical Conference` | — |
| 37 | Annual Report | — | — | EXP `Annual Report` | — |
| 38 | Statistics | — | — | EXP `Statistics` | — |

\* OpenAlex conference papers: `type=article` + `primary_location.source.type=conference`.

### REV: Review or Other Citation

#### Reviews & Syntheses

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 39 | Review | REV `review` | — | REV `Review` | REV `Review` |
| 40 | Systematic Review | — | — | REV `Systematic Review` | — |
| 41 | Meta-Analysis | — | — | REV `Meta-Analysis` | REV `MetaAnalysis` |
| 42 | Network Meta-Analysis | — | — | REV `Network Meta-Analysis` | — |
| 43 | Scoping Review | — | — | REV `Scoping Review` | — |
| 44 | Scientific Integrity Review | — | — | REV `Scientific Integrity Review` | — |

#### Editorial & Commentary

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 45 | Editorial | REV `editorial` | — | REV `Editorial` | REV `Editorial` |
| 46 | Letter | REV `letter` | — | REV `Letter` | REV `LettersAndComments` |
| 47 | Comment | — | — | REV `Comment` | REV `LettersAndComments` |
| 48 | News | — | — | REV `News` | REV `News` |
| 49 | Newspaper Article | — | — | REV `Newspaper Article` | — |
| 50 | Interview | — | — | REV `Interview` | — |
| 51 | Address | — | — | REV `Address` | — |
| 52 | Introductory Journal Article | — | — | REV `Introductory Journal Article` | — |
| 53 | Meeting Abstract | — | — | REV `Meeting Abstract` | — |
| 54 | Popular Work | — | — | REV `Popular Work` | — |
| 55 | Blog | — | — | REV `Blog` | — |
| 56 | Webcast | — | — | REV `Webcast` | — |

#### Corrections & Retractions

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 57 | Erratum | REV `erratum` | — | REV `Published Erratum` | — |
| 58 | Retraction notice | REV `retraction` | — | REV `Retraction of Publication` | — |
| 59 | Retracted Publication | — | — | REV `Retracted Publication` | — |
| 60 | Corrected and Republished Article | — | — | REV `Corrected and Republished Article` | — |
| 61 | Expression of Concern | — | — | REV `Expression of Concern` | — |
| 62 | Duplicate Publication | — | — | REV `Duplicate Publication` | — |

#### Books & Monographs

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 63 | Book | REV `book` | REV `book` | — | REV `Book` |
| 64 | Book Chapter | REV `book-chapter` | REV `book-chapter` | — | REV `BookSection` |
| 65 | Book Section | REV `book-section` | REV `book-section` | — | — |
| 66 | Book Part | — | REV `book-part` | — | — |
| 67 | Book Track | — | REV `book-track` | — | — |
| 68 | Book Set | — | REV `book-set` | — | — |
| 69 | Book Series | — | REV `book-series` | — | — |
| 70 | Edited Book | — | REV `edited-book` | — | — |
| 71 | Reference Book | — | REV `reference-book` | — | — |
| 72 | Monograph | — | REV `monograph` | REV `Monograph` | — |
| 73 | Book Review | — | — | REV `Book Review` | — |
| 74 | Book Illustrations | — | — | REV `Book Illustrations` | — |
| 75 | Collected Work | — | — | REV `Collected Work` | — |
| 76 | Collection | — | — | REV `Collection` | — |
| 77 | Festschrift | — | — | REV `Festschrift` | — |

#### Reference & Encyclopedic

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 78 | Reference Entry | REV `reference-entry` | REV `reference-entry` | — | — |
| 79 | Encyclopedia | — | — | REV `Encyclopedia` | — |
| 80 | Dictionary | — | — | REV `Dictionary` | — |
| 81 | Dictionary, Chemical | — | — | REV `Dictionary, Chemical` | — |
| 82 | Dictionary, Classical | — | — | REV `Dictionary, Classical` | — |
| 83 | Dictionary, Dental | — | — | REV `Dictionary, Dental` | — |
| 84 | Dictionary, Medical | — | — | REV `Dictionary, Medical` | — |
| 85 | Dictionary, Pharmaceutic | — | — | REV `Dictionary, Pharmaceutic` | — |
| 86 | Dictionary, Polyglot | — | — | REV `Dictionary, Polyglot` | — |
| 87 | Terminology | — | — | REV `Terminology` | — |
| 88 | Atlas | — | — | REV `Atlas` | — |
| 89 | Pharmacopoeia | — | — | REV `Pharmacopoeia` | — |
| 90 | Pharmacopoeia, Homeopathic | — | — | REV `Pharmacopoeia, Homeopathic` | — |
| 91 | Formulary | — | — | REV `Formulary` | — |
| 92 | Formulary, Dental | — | — | REV `Formulary, Dental` | — |
| 93 | Formulary, Homeopathic | — | — | REV `Formulary, Homeopathic` | — |
| 94 | Formulary, Hospital | — | — | REV `Formulary, Hospital` | — |
| 95 | Dispensatory | — | — | REV `Dispensatory` | — |
| 96 | Herbal | — | — | REV `Herbal` | — |

#### Guidelines & Consensus

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 97 | Guideline | — | — | REV `Guideline` | — |
| 98 | Practice Guideline | — | — | REV `Practice Guideline` | — |
| 99 | Consensus Development Conference | — | — | REV `Consensus Development Conference` | — |
| 100 | Consensus Development Conference, NIH | — | — | REV `Consensus Development Conference, NIH` | — |

#### Standards

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 101 | Standard | REV `standard` | REV `standard` | — | — |

#### Journal / Proceedings Infrastructure

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 102 | Paratext | REV `paratext` | — | — | — |
| 103 | Libguides | REV `libguides` | — | — | — |
| 104 | Journal (container) | — | REV `journal` | — | — |
| 105 | Journal Issue | — | REV `journal-issue` | — | — |
| 106 | Journal Volume | — | REV `journal-volume` | — | — |
| 107 | Proceedings (container) | — | REV `proceedings` | — | — |
| 108 | Proceedings Series | — | REV `proceedings-series` | — | — |
| 109 | Report Series | — | REV `report-series` | — | — |
| 110 | Periodical | — | — | REV `Periodical` | — |
| 111 | Periodical Index | — | — | REV `Periodical Index` | — |

#### Grants & Funding

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 112 | Grant | REV `grant` | REV `grant` | — | — |
| 113 | Research Support, ARRA | — | — | REV `Research Support, American Recovery and Reinvestment Act` | — |
| 114 | Research Support, NIH Extramural | — | — | REV `Research Support, N.I.H., Extramural` | — |
| 115 | Research Support, NIH Intramural | — | — | REV `Research Support, N.I.H., Intramural` | — |
| 116 | Research Support, Non-U.S. Gov't | — | — | REV `Research Support, Non-U.S. Gov't` | — |
| 117 | Research Support, U.S. Gov't Non-PHS | — | — | REV `Research Support, U.S. Gov't, Non-P.H.S.` | — |
| 118 | Research Support, U.S. Gov't PHS | — | — | REV `Research Support, U.S. Gov't, P.H.S.` | — |
| 119 | Research Support, U.S. Government | — | — | REV `Research Support, U.S. Government` | — |
| 120 | Support of Research | — | — | REV `Support of Research` | — |

#### Biographical & Historical

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 121 | Biography | — | — | REV `Biography` | — |
| 122 | Autobiography | — | — | REV `Autobiography` | — |
| 123 | Biobibliography | — | — | REV `Biobibliography` | — |
| 124 | Bibliography | — | — | REV `Bibliography` | — |
| 125 | Classical Article | — | — | REV `Classical Article` | — |
| 126 | Historical Article | — | — | REV `Historical Article` | — |
| 127 | Personal Narrative | — | — | REV `Personal Narrative` | — |
| 128 | Eulogy | — | — | REV `Eulogy` | — |
| 129 | Portrait | — | — | REV `Portrait` | — |
| 130 | Diary | — | — | REV `Diary` | — |
| 131 | Collected Correspondence | — | — | REV `Collected Correspondence` | — |

#### Educational & Instructional

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 132 | Textbook | — | — | REV `Textbook` | — |
| 133 | Handbook | — | — | REV `Handbook` | — |
| 134 | Laboratory Manual | — | — | REV `Laboratory Manual` | — |
| 135 | Study Guide | — | — | REV `Study Guide` | — |
| 136 | Resource Guide | — | — | REV `Resource Guide` | — |
| 137 | Guidebook | — | — | REV `Guidebook` | — |
| 138 | Lecture | — | — | REV `Lecture` | — |
| 139 | Lecture Note | — | — | REV `Lecture Note` | — |
| 140 | Nurses Instruction | — | — | REV `Nurses Instruction` | — |
| 141 | Patient Education Handout | — | — | REV `Patient Education Handout` | — |
| 142 | Interactive Tutorial | — | — | REV `Interactive Tutorial` | — |
| 143 | Programmed Instruction | — | — | REV `Programmed Instruction` | — |
| 144 | Examination Questions | — | — | REV `Examination Questions` | — |
| 145 | Problems and Exercises | — | — | REV `Problems and Exercises` | — |
| 146 | Cookbook | — | — | REV `Cookbook` | — |

#### Visual / Media

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 147 | Photograph | — | — | REV `Photograph` | — |
| 148 | Drawing | — | — | REV `Drawing` | — |
| 149 | Pictorial Work | — | — | REV `Pictorial Work` | — |
| 150 | Caricature | — | — | REV `Caricature` | — |
| 151 | Cartoon | — | — | REV `Cartoon` | — |
| 152 | Graphic Novel | — | — | REV `Graphic Novel` | — |
| 153 | Map | — | — | REV `Map` | — |
| 154 | Poster | — | — | REV `Poster` | — |
| 155 | Postcard | — | — | REV `Postcard` | — |
| 156 | Bookplate | — | — | REV `Bookplate` | — |
| 157 | Broadside | — | — | REV `Broadside` | — |
| 158 | Architectural Drawing | — | — | REV `Architectural Drawing` | — |
| 159 | Animation | — | — | REV `Animation` | — |
| 160 | Documentaries and Factual Films | — | — | REV `Documentaries and Factual Films` | — |
| 161 | Instructional Film and Video | — | — | REV `Instructional Film and Video` | — |
| 162 | Unedited Footage | — | — | REV `Unedited Footage` | — |
| 163 | Video-Audio Media | — | — | REV `Video-Audio Media` | — |

#### Literary / Miscellaneous

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 164 | Essay | — | — | REV `Essay` | — |
| 165 | Poetry | — | — | REV `Poetry` | — |
| 166 | Fictional Work | — | — | REV `Fictional Work` | — |
| 167 | Juvenile Literature | — | — | REV `Juvenile Literature` | — |
| 168 | Wit and Humor | — | — | REV `Wit and Humor` | — |
| 169 | Anecdotes | — | — | REV `Anecdotes` | — |
| 170 | Aphorisms and Proverbs | — | — | REV `Aphorisms and Proverbs` | — |
| 171 | Phrases | — | — | REV `Phrases` | — |
| 172 | Sermon | — | — | REV `Sermon` | — |
| 173 | Funeral Sermon | — | — | REV `Funeral Sermon` | — |
| 174 | Movable Books | — | — | REV `Movable Books` | — |

#### Administrative / Catalogs / Legal

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 175 | Catalog | — | — | REV `Catalog` | — |
| 176 | Catalog, Bookseller | — | — | REV `Catalog, Bookseller` | — |
| 177 | Catalog, Commercial | — | — | REV `Catalog, Commercial` | — |
| 178 | Catalog, Drug | — | — | REV `Catalog, Drug` | — |
| 179 | Catalog, Publisher | — | — | REV `Catalog, Publisher` | — |
| 180 | Catalog, Union | — | — | REV `Catalog, Union` | — |
| 181 | Directory | — | — | REV `Directory` | — |
| 182 | Index | — | — | REV `Index` | — |
| 183 | Union List | — | — | REV `Union List` | — |
| 184 | Price List | — | — | REV `Price List` | — |
| 185 | Legal Case | — | — | REV `Legal Case` | — |
| 186 | Legislation | — | — | REV `Legislation` | — |
| 187 | Government Publication | — | — | REV `Government Publication` | — |
| 188 | Public Service Announcement | — | — | REV `Public Service Announcement` | — |
| 189 | Advertisement | — | — | REV `Advertisement` | — |
| 190 | Prospectus | — | — | REV `Prospectus` | — |

#### Format / Meta-types

| # | Тип публикации | OpenAlex | CrossRef | PubMed | Semantic Scholar |
|--:|---|:---:|:---:|:---:|:---:|
| 191 | Other | REV `other` | REV `other` | — | — |
| 192 | Abbreviations | — | — | REV `Abbreviations` | — |
| 193 | Abstracts | — | — | REV `Abstracts` | — |
| 194 | English Abstract | — | — | REV `English Abstract` | — |
| 195 | Chart | — | — | REV `Chart` | — |
| 196 | Chronology | — | — | REV `Chronology` | — |
| 197 | Tables | — | — | REV `Tables` | — |
| 198 | Form | — | — | REV `Form` | — |
| 199 | Outline | — | — | REV `Outline` | — |
| 200 | Almanac | — | — | REV `Almanac` | — |
| 201 | Calendar | — | — | REV `Calendar` | — |
| 202 | Ephemera | — | — | REV `Ephemera` | — |
| 203 | Program | — | — | REV `Program` | — |
| 204 | Manuscript | — | — | REV `Manuscript` | — |
| 205 | Manuscript, Medical | — | — | REV `Manuscript, Medical` | — |
| 206 | Incunabula | — | — | REV `Incunabula` | — |
| 207 | Unpublished Work | — | — | REV `Unpublished Work` | — |
| 208 | Web Archive | — | — | REV `Web Archive` | — |
| 209 | Account Book | — | — | REV `Account Book` | — |
| 210 | Overall | — | — | REV `Overall` | — |
| 211 | Publication Components | — | — | REV `Publication Components` | — |
| 212 | Publication Formats | — | — | REV `Publication Formats` | — |
| 213 | Study Characteristics | — | — | REV `Study Characteristics` | — |
| 214 | Exhibition | — | — | REV `Exhibition` | — |

---

## Summary Statistics

| Provider | Total types | PEER | EXP | REV |
|---|---:|---:|---:|---:|
| OpenAlex | 24 | 1 | 11 | 12 |
| CrossRef | 30 | 1 | 7 | 22 |
| PubMed | 189 | 0 | 37 | 152 |
| Semantic Scholar | 13 | 0 | 7 | 6 |

### Quick-filter sets (API values for pipeline filtering)

**OpenAlex PEER filter:**
```
peer-review
```

**OpenAlex EXP filter:**
```
article,preprint,dataset,database,dissertation,report,report-component,software,supplementary-materials
```

**CrossRef PEER filter:**
```
peer-review
```

**CrossRef EXP filter:**
```
journal-article,proceedings-article,posted-content,dataset,database,dissertation,report,report-component,component
```

**PubMed EXP filter (most common):**
```
Journal Article,Clinical Trial,Randomized Controlled Trial,Controlled Clinical Trial,
Clinical Study,Observational Study,Comparative Study,Validation Study,Multicenter Study,
Case Reports,Dataset,Preprint,Academic Dissertation,Patent,Technical Report
```

**Semantic Scholar EXP filter:**
```
JournalArticle,Conference,Study,CaseReport,ClinicalTrial,Dataset
```

# TRIAGE SUMMARY — CR-FULL-20260816 / #8890

Ground truth: current code, tests, contracts, and executable reproductions
outrank CodeRabbit output.

- Review BASE_SHA: `6a2c8abe8ac5501bae3fef69667c3ff09280e46c`
- Verification checkout: `c923bdc89a6297806457615c559bfff06f38567e`
- Disposition completed: 2026-08-17
- Parent triage stream: [#8890](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8890)

## #8890 scope

All ok leaves listed by #8890 have an explicit canonical disposition.

| Leaf | Raw | confirm | reject | pending |
| --- | ---: | ---: | ---: | ---: |
| `S01-domain-types` | 36 | 15 | 21 | 0 |
| `S01-domain-value_objects` | 41 | 18 | 23 | 0 |
| `S01-domain-schemas` | 42 | 6 | 36 | 0 |
| `S03-app-control-plane` | 130 | 47 | 83 | 0 |
| `S04-app-services-other` | 184 | 65 | 119 | 0 |
| `S10-interfaces-cli` | 82 | 39 | 43 | 0 |
| `S01-domain-validation` | 7 | 2 | 5 | 0 |
| `S01-domain-transformations` | 6 | 3 | 3 | 0 |
| `S01-domain-workflow` | 5 | 2 | 3 | 0 |
| `S02-app-core` | 159 | 44 | 115 | 0 |
| `S11-interfaces-http` | 64 | 30 | 34 | 0 |
| **#8890 total** | **756** | **271** | **485** | **0** |

The campaign directory also contains pending records from leaves outside
#8890. They were not silently disposed by this task.

## Critical dispositions

| Finding | Disposition | Ground-truth evidence |
| --- | --- | --- |
| `S01-domain-types-018` | confirm | malformed semantic-version cardinalities violate `ContractIdentity.validate()`; linked to #8893 |
| `S01-domain-types-022` | confirm | single-mode rollout defaults violate the active-version invariant; linked to #8893 |
| `S03-app-control-plane-117` | confirm | mixed `query=None` / `query=str` source-reference keys raise `TypeError` during sorting |
| `S04-app-services-other-083` | confirm | mixed offset-naive / offset-aware terminal timestamps raise `TypeError` in `max()` |
| `S04-app-services-other-171` | confirm | `_rm_tree` follows a directory symlink and deletes content outside the requested tree |
| `S04-app-services-other-184` | confirm | a relative runtime root recursively prepends itself until `RecursionError` |
| `S10-interfaces-cli-014` | reject | `checkpoint_inspect` already accepts and forwards `manifest_id`; the alleged alternate command is absent at BASE and HEAD |
| `S10-interfaces-cli-019` | confirm | invalid config paths print errors but retain exit status 0 |
| `S10-interfaces-cli-082` | confirm | the POSIX `ss` parser matches a peer port anywhere on the line as if it were the local listener |

The six newly reviewed critical confirms have current-tree evidence recorded in
`TRIAGE_OVERRIDES.json`; the two earlier type criticals remain linked to #8893.
No product implementation was performed in this triage task.

## Confirm sets

Every other ordinal in each #8890 leaf is `reject`.

- `S01-domain-types`: 004, 010–019, 022–023, 026, 028
- `S01-domain-value_objects`: 003–007, 011, 018–024, 028–029, 031, 033, 039
- `S01-domain-schemas`: 008, 022, 028, 031, 033, 041
- `S01-domain-validation`: 003, 007
- `S01-domain-transformations`: 004–006
- `S01-domain-workflow`: 002, 005
- `S03-app-control-plane`: 004, 009, 012, 016–017, 020, 022–023, 026, 031, 033–035, 041, 043, 045–046, 050–054, 057, 066–067, 069, 072, 078–079, 083, 085, 087, 098–100, 103, 109, 111–115, 117, 121, 124, 126–127
- `S04-app-services-other`: 002, 012, 014, 020, 022–024, 026, 028, 031, 033, 043, 045, 047, 049–051, 053, 055–056, 058–059, 061, 064, 066–067, 069–070, 072, 077, 083, 090, 097, 100, 103, 105, 109, 112, 117, 129–131, 134–135, 138–139, 143–144, 151–157, 167–171, 175, 177, 180, 182, 184
- `S10-interfaces-cli`: 001, 004, 008, 010–011, 013, 015–016, 018–020, 022–024, 031–032, 034, 037–038, 045–046, 049, 054, 057, 059–063, 068–069, 073, 076–082
- `S02-app-core`: 009, 011–012, 014, 016, 018, 023, 026–028, 036, 038, 040, 047, 049, 054, 058, 060, 064–065, 067, 071–073, 075, 078, 082, 090–091, 100, 102–104, 116–117, 124–125, 128, 135, 137, 148, 150, 153, 156
- `S11-interfaces-http`: 006–007, 010, 012–013, 024, 026–029, 035, 037–038, 040–042, 044–047, 049–051, 055–056, 058–059, 061–062, 064

## Rejected classes

The rejects include style/DRY/refactor-only suggestions, test-only or
docstring-only requests, Protocol/typing-only changes, ADR or release work for
already-shipped APIs, inventory-hash-only maintenance, contract expansion, and
claims for which current code/tests did not establish an invariant breach.
Previously fixed #8643/#8644/#8645/#8652 behavior was not reopened without a
fresh regression.

## Earlier completed leaves

The five leaves completed before #8890 remain linked to #8863 and retain their
114 canonical dispositions:

| Leaf | Raw | confirm | reject |
| --- | ---: | ---: | ---: |
| `S01-domain-aggregates` | 17 | 1 | 16 |
| `S01-domain-behavior` | 51 | 18 | 33 |
| `S01-domain-composite` | 27 | 9 | 18 |
| `S01-domain-config` | 13 | 1 | 12 |
| `S01-domain-contracts` | 6 | 3 | 3 |
| **earlier total** | **114** | **32** | **82** |

Earlier #8890 streams remain grouped as follows: type criticals on #8893,
remaining type confirms on #8895, and value-object/schema confirms on #8905.

## Canonical ledgers

- `TRIAGE_OVERRIDES.json` — source dispositions keyed by stable fingerprint
- `FINDINGS.jsonl` / `FINDINGS.md` — normalized campaign findings
- `TRIAGE.md` — human-readable per-finding disposition and evidence
- `DE_DUPE_MAP.json` — fingerprint and duplicate map
- `ISSUES_MAP.json` / `ISSUES_CREATED.md` — already linked grouped streams

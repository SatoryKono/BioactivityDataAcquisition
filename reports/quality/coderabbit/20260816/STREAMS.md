# Implementation streams — CR-FULL 20260816

Exclusive streams for accepted (`confirm`) findings. All listed product
streams are closed on `main` as of 2026-08-17.

| Stream | Issue | Findings | Priority | Scope | State |
|---|---:|---:|---|---|---|
| `domain-20260816-five-leaves` | #8863 | 32 | P1 | first-five ok leaves | closed |
| `domain-20260816-types-criticals` | #8893 | 2 | P1 | types-018 / types-022 | closed |
| `domain-20260816-identity-json` | #8891 | 8 | P1 | residual-root + normalization identity/JSON | closed |
| `domain-20260816-freeze-catalogs` | #8888 | 3 | P1 | FrozenList/Dict, PubChem catalog, ReasonCatalog | closed |
| `domain-20260816-run-report-accounting` | #8889 | 4 | P1 | measured-zero / catalog / top-N | closed |
| `later-leaf-ok-triage` | #8890 | 756 raw | P2 | independent triage; criticals promoted | closed |
| `domain-20260816-types-remaining` | #8895 | 13 | P1 | remaining types confirms | closed |
| `domain-20260816-vo-schemas` | #8905 | 24 | P1 | VO fail-closed + schema | closed |
| `app-utc-timestamps` | #8908 | 2 | P1 | naive vs aware timestamps | closed |
| `control-plane-source-refs` | #8907 | 3 | P1 | source-ref sort/normalize | closed |
| `run-report-fs-safety` | #8909 | 7 | P1 | `_rm_tree` / runtime path | closed |
| `cli-fail-closed` | #8910 | 14 | P1 | CLI exit semantics | closed |
| `health-probe` | #8911 | 10 | P1 | `ss` listener parse | closed |
| `infra-20260816-fail-closed` | #8916 | 16 | P1 | join `.0`, Silver FK, Arrow, time-travel, empty keys | closed |
| `security-20260816-redaction` | #8917 | 6 | P1 | Bearer/VCR/salt/argv | closed |
| `app-20260816-fail-closed` | #8918 | 20 | P1 | manifest, replay sort, FK blanks, lock, pmc_id | closed |

Unlinked leftover confirms from #8890 bulk triage are bound to closed #8890
(no new per-finding GitHub issues). Do not reopen #8643 / #8644 / #8645 / #8652
without a fresh reproduction.

Exact-cover retries of CodeRabbit service-blocked leaves remain documented in
`BLOCKERS.md` / `FINAL.md`.

You are reviewing BioETL (hexagonal + DDD + medallion + local-only ADR-010).

Rules:
- Domain must stay I/O-free; DI only in composition.
- Prefer evidence: path + symbol + broken invariant.
- Do not propose increasing quality/debt budgets.
- Do not treat Docker/monitoring as required default.
- DQ hard_fail is multi-default (hierarchical 0.50 vs Silver-request 0.20).
- Ignore pure style nits unless they hide correctness risk.
- Skip themes already closed in ARCH-CR / DOC-GOV / prior CR residual packs
  unless you prove regression on current BASE_SHA.
- Prefer residual risks that escape unit tests: concurrency, lineage, quarantine,
  FK reconciliation, determinism/replay, secret leakage, gate honesty, contract drift.
- Do not reopen already fixed #8643/#8644/#8645/#8652 findings unless a fresh
  reproduction proves regression on this BASE_SHA.

Output for EACH finding (machine-parseable):
1) severity: critical | major | minor | trivial
2) path: repo-relative
3) claim: one sentence
4) why it matters: invariant / ADR / RULES id if possible
5) suggested fix class: code | test | config | docs
6) acceptance check: command or test name if possible
7) confidence: high | medium | low

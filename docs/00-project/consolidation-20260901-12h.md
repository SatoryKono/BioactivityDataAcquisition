# Consolidation 20260901 last-12h

Base: origin/main 497769829c (current GitHub main after medallion-cycle merge).

Unique remaining product from branches with commits in the last 12 hours, after skipping tips whose two-dot delta would regress later main:

Included:

- fix/observability-grafana-bootstrap-20260901 (51a3bbdc5a, PR #9951): Grafana soft-bootstrap retry after Ops HTTP start race; exact-run Processed Records stay on RunLedger (UNKNOWN when empty; DASH-SCOPE-001 / DASH-STATE-001 / DASH-DATA-002). Overlay kept after origin/main merged observability-stack-read-path prometheus empty-ledger fallback.
- fix/root-hygiene-tmp-txt-5581 (5f22c1595d) unique files only: tests/helpers/isolated_git.py, memory/proof git isolation, /tmp_*.txt gitignore. Not the stale two-dot tip (would revert prompt dedupe and Grafana plugins).

Already on origin/main (not re-merged):

- #9950 medallion/bronze exclusive publish (squash 3118887785)
- #9952 / 8283edd9e0 architecture hash rebind and bronze ruff whitespace
- 8526d0ce69 / 12323 BronzeWriterIOMixin whitespace
- 984310c134 dash-fit-004 Trust 906 / Overview 215
- 7e07673573 temp-branch
- 8866ba2944 / c4281511f4 prompt megacard retirement ADR-060 (#9946)
- 0f606a5a8b observability-stack-read-path (bronze docs + empty-ledger prometheus fallback on main; fallback overlay reverted in this branch)

Explicitly skipped as stale two-dot / contract regression:

- 8ec35d1327 / 76fdd5419e empty-ledger prometheus fallback as current for a selected UUID
- 0e15fbf361 retire optional Grafana plugins (would delete React-19 plugin trees already on main)
- master20260901-*, bolt, already-merged #9920-#9949 topic tips

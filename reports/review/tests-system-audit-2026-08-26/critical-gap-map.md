# Critical gap map (tests-system)

Each gap → production / release risk. No invented coverage targets.

| Gap id | Test / lane gap | Production risk | PR gate today | Finding |
| --- | --- | --- | --- | --- |
| G1 | `@pytest.mark.slow` never collected under default addopts | Secrets in committed VCR cassettes can land; full-chain e2e and some architecture wrappers never execute | `TestVCRCassetteSanitization` not in Tests security group; detect-secrets covers source secrets separately | TEST-SYS-001 |
| G2 | GitHub required checks disabled on `main` | Broken tests/coverage can be merged/pushed; release integrity is social | Workflows still *run* on PR but do not block merge | TEST-SYS-002 |
| G3 | integration-replay + unit-fast via xdist `-n auto` | VCR/order races → false green or flakes; local serial cannot reproduce CI | test-matrix/test-fast jobs | TEST-SYS-003 |
| G4 | e2e skips not in skip inventory; SLO advisory | Entity pipelines skip closed without owner/expiry; nightly skip rate not blocking | matrix-smoke 15% on run3 only | TEST-SYS-004 TEST-SYS-005 |
| G5 | 16 deferred matrix pipelines; `chembl.publication_term` e2e owner not in e2e-smoke | Derived publication_term / composites / several chembl entities lack PR e2e cycle | unit/integration owners where present; publication_term transformer unit only | TEST-SYS-006 |
| G6 | Non-critical VCR mismatch → skip | Adapter contract drift on non-critical active rows looks green | CRITICAL_SMOKE_PIPELINES still fail | TEST-SYS-007 |
| G7 | Live provider contracts monthly only | Silent upstream API break until 1st-of-month (or manual dispatch) | offline contract-confidence on PR | accepted policy (ADR-042); not a new P0 |
| G8 | Broad application mutation staged | Undertested application mutants outside curated slices | domain 70% + control-plane/export/workflow slices | ADR-042 documented; not raised as finding |

## Negative / auth / schema

- Auth/secret: source detect-secrets on PR (`security.yml`); VCR *content* sanitization is the slow class (G1).
- Schema: `tests/contract/` gold/silver snapshots on `contract-confidence` (`no_api or not network`).
- Negative paths: present in unit/integration (DQ threshold, VCR mismatch fail for critical smoke). Non-critical mismatch skip is G6.

## Isolation residual

- Time/random: `tests/helpers/clock.py` FixedClock; uuid4 budget 0 in `test_governance_audit.yaml`.
- Network: contract opt-in; no pytest-socket (domain unit purity AST guards instead).
- Temp/cwd: session autouse pins cwd to repo root; e2e uses `e2e_data_dir`.

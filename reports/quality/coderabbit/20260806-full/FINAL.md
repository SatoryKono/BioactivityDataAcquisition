# FINAL — CR-FULL-20260806-full

- **State:** **PARTIAL** (CodeRabbit `rate_limit` mid Wave A)
- **Prompt:** `reports/quality/coderabbit/PROMPT_FULL_PROJECT_AUDIT.md`
- **CodeRabbit CLI:** 0.7.2 (`--agent --light`, orphan empty-base scopes via bare clone)
- **Runtime artifacts:** `/tmp/bioetl-cr-artifacts/20260806-full/`
- **Host mirror:** `reports/quality/coderabbit/20260806-full/`
- **BASE_SHA:** see `BASE_SHA.txt`

## Scope matrix (Phase 0 — complete)

| Item | Value |
|------|-------|
| Leaves planned | **118** (full project surfaces) |
| Cap | ≤300 files / leaf |
| Over-cap | 0 |
| Waves | A (31), B, C, D, E, F, R residual |
| Preflight | `00-preflight.md` |
| Matrix | `01-scope-matrix.md` / `.json` |

## CLI execution (Phase 1 — partial)

| Leaf | Status | Findings |
|------|--------|---------:|
| `S01-domain-lineage` | ok | 3 |
| `S01-domain-aggregates` | ok | 8 |
| `S01-domain-behavior` | ok | 51 |
| `S01-domain-composite` | **rate_limit** (retry failed → hard stop) | 0 |

- Progress leaves: **4 / 118**
- Findings counted on OK leaves: **62**
- Deduped findings in corpus (includes prior domain-retry logs merged): **132**
  - critical: 3 · major: 64 · minor: 28 · trivial: 37

**BLOCKER issue:** [#8215](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8215)

## Findings / triage (Phase 2)

- `FINDINGS.md` / `FINDINGS.jsonl`
- `TRIAGE.md` — default CONFIRM for non-empty findings
- `DE_DUPE_MAP.json`

## GitHub issues (Phase 3 — mandatory per problem)

| Metric | Value |
|--------|------:|
| Map rows (1:1 accepted findings) | **132** |
| Unique issue numbers | **107** |
| `created` this campaign publish | **43** |
| `linked_existing` | **89** |
| `failed` | **0** |

Index: `ISSUES_CREATED.md`, `ISSUES_MAP.json`  
Issue number range observed: **#8096–#8214** (+ blocker **#8215**).

## Streams (Phase 4 — draft from filed issues)

Path-exclusive groups for parallel implement (domain-heavy partial set):

| Stream | Focus |
|--------|--------|
| **S1** | `domain/entities/**` |
| **S2** | `domain/exceptions/**` |
| **S3** | `domain/value_objects/**` |
| **S4** | `domain/behavior`, `aggregates`, `lineage` |
| **S5** | other domain residual |

Full table: regenerate via `parse_and_publish` after more leaves; see issue list in `ISSUES_CREATED.md`.

## Not done yet

- [ ] Remaining Wave A leaves + Waves B–F + residual R (~114 leaves)
- [ ] Re-audit after fixes
- [ ] Full stream rebalance after complete issue set

## Resume (after rate-limit cooldown, often 30–60+ min)

```bash
# WSL
export PATH="$HOME/.local/bin:$PATH"
export OUT_DIR=/tmp/bioetl-cr-artifacts/20260806-full
export MATRIX=$OUT_DIR/01-scope-matrix.json
export MAIN_REPO=/mnt/e/github/BioactivityDataAcquisition
# progress.json keeps OK leaves; failed/rate_limit will retry
python3 -u $OUT_DIR/scripts/run_all.py
python3 $OUT_DIR/scripts/parse_and_publish.py
# mirror
cp -f $OUT_DIR/{FINDINGS*,TRIAGE.md,ISSUES_*,DE_DUPE_MAP.json,progress.json,FINAL.md} \
  $MAIN_REPO/reports/quality/coderabbit/20260806-full/
```

## Constraints honored

- No tech-debt / quality budget growth
- No `.env` edits
- Artifacts under allowlisted `reports/quality/coderabbit/**` (+ `/tmp` runtime)
- **GH issue for every accepted finding** applied to all findings parsed so far

## DoD checklist

- [x] Preflight + full scope matrix
- [~] CLI logs for all leaves — **blocked by rate_limit**
- [x] FINDINGS + TRIAGE + DE_DUPE for captured findings
- [x] GH issues for accepted findings (created/linked, 0 failed)
- [x] Stream plan draft
- [x] FINAL.md (honest partial status)
- [x] Rate-limit blocker GH issue (#8215)

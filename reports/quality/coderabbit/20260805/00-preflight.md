# CR-FULL-00 Preflight — 2026-08-05

**Issue:** #7689  
**Epic:** #7688  
**Status:** COMPLETED  
**Worktree:** `C:/Users/Fedor/bioetl-cr-full-preflight`  
**Branch:** `audit/cr-full-preflight`

## 1. Baseline freeze

| Field | Value |
| --- | --- |
| Target branch | `main` |
| `BASE_SHA` | `8b9ac1e7401e5dd172adf89e1f2626483b111265` |
| Tip subject | `docs(issues): add CodeRabbit full residual campaign issue pack` |
| Isolation | dedicated worktree; hard-reset to `origin/main`; clean status |

```bash
git fetch origin main
git worktree add -B audit/cr-full-preflight C:/Users/Fedor/bioetl-cr-full-preflight origin/main
git -C C:/Users/Fedor/bioetl-cr-full-preflight rev-parse HEAD
# → 8b9ac1e7401e5dd172adf89e1f2626483b111265
```

## 2. Tool versions

| Tool | Version / status |
| --- | --- |
| Python (host) | 3.13.7 |
| ruff (host, lockfile-aligned) | **0.15.22** (matches `uv.lock`) |
| CodeRabbit CLI (host Git Bash) | **NOT_INSTALLED** |
| CodeRabbit CLI (WSL) | **0.7.1** at `/home/fedor/.local/bin/coderabbit` |
| WSL | present |
| Host OS | Windows 10 + MSYS/Git Bash |
| `CODERABBIT_API_KEY` (host shell) | **absent** |
| `CODERABBIT_API_KEY` (WSL env) | **absent** |
| Repo secret `CODERABBIT_API_KEY` (CI) | **absent** — run `31020678618` warning: Skipping CLI review |
| GitHub App install (API) | **[incomplete]** — installation endpoint 401 with available token |
| CodeRabbit PR App | config ready (`.coderabbit.yaml`); App install not proven via API |

## 3. CodeRabbit channels

| Channel | Evidence | Ready for residual waves? |
| --- | --- | --- |
| PR App + `.coderabbit.yaml` | `profile: assertive` on disk | Continuous PR review config ready; App install [incomplete] |
| CI CLI workflow | push runs **success** but **skips** without secret | **Blocked** until #7698 |
| Local/WSL CLI | CLI 0.7.1 in WSL; no API key | **Blocked** until operator injects key (never commit) |

## 4. Ground-truth gates (before CR waves)

| Gate | Command | Result |
| --- | --- | --- |
| Root hygiene | `python -m scripts.engineering.repo check-cleanliness` | **OK** (37 root files, 15 root dirs) |
| Ruff lint | `ruff==0.15.22 check .` | **All checks passed** |
| Ruff format | `ruff==0.15.22 format --check .` | **5141 files already formatted** |
| Arch subset | `pytest` strict contracts + layer deps + CLI registry | **40 passed** |
| Skill mirrors | `sync_ai_governance --only skill-mirrors --check` | **FAIL** (8 skills: py-review-orchestrator, py-test-bot, py-test-swarm, repo-config, research-workflow, technical-designer-mermaid, vcr-record, verify-architecture) |
| `make qa-arch-fast` | sharded architecture-fast-boundary | **not fully executed**; boundary subset used |

### Debt / scorecard (no budget change)

- Registry: `configs/quality/technical_debt_audit_registry.yaml`
- Current audit: `total-tech-debt-main-2026-07-27-r1`
- `audited_commit_sha`: `14bcbfbd8054292fff9f55837da508a80ceaaeea` (**stale vs BASE_SHA**)
- Linked issue: `#7038`
- Preflight does not refresh debt evidence or grow budgets.

## 5. File-count matrix (S01–S20)

Counted via `git ls-files` on BASE_SHA.

| Scope | Path(s) | Files | Split ≥300? |
| --- | --- | ---: | --- |
| S01 domain | `src/bioetl/domain` | 594 | **YES** |
| S02 app-core | `application/core` | 192 | no |
| S03 app-control-plane | `services/control_plane` | 140 | no |
| S04 app-services-other | services excl CP | 143 | no |
| S05 app-pipelines | `application/pipelines` | 99 | no |
| S06 infra-adapters | `infrastructure/adapters` | 188 | no |
| S07 infra-http-storage | http+storage+delta | 143 | no |
| S08 infra-observability | `observability` | 57 | no |
| S09 composition | `composition` | 283 | no (near cap) |
| S10 interfaces-cli | `interfaces/cli` | 104 | no |
| S11 interfaces-http | `interfaces/http` | 46 | no |
| S12 tests-architecture | `tests/architecture` | 491 | **YES** |
| S13 tests-unit-domain | `tests/unit/domain` | 323 | **YES** |
| S14 tests-unit-application | `tests/unit/application` | 379 | **YES** |
| S15 tests-integration | `tests/integration` | 219 | no |
| S16 configs-quality | `configs/quality` | 97 | no |
| S17 docs-normative | `docs/00-project` + decisions | 373 | **YES** |
| S18 grafana | grafana + dashboard guides | 156 | no |
| S19 scripts-engineering | `scripts/engineering` | 215 | no |
| S20 security-surface | `tests/security` | 12 | no |

**Ready without split:** S02–S11, S15–S16, S18–S20.

### Required splits

| Scope | Proposed split |
| --- | --- |
| S01 (594) | domain/ports(76), normalization(88), behavior(52), schemas(49), value_objects(41), entities(27), control_plane(32), composite(26), + residual packs ≤250 |
| S12 (491) | two basename halves or theme packs (boundary vs debt closeout) |
| S13 (323) | two packs ~160 |
| S14 (379) | core vs services vs other |
| S17 (373) | decisions(63) separate; further split `docs/00-project` if needed |

## 6. Scopes ready (Wave A start order)

After secret available:

1. S09 composition (283)  
2. S03 app-control-plane (140)  
3. S02 app-core (192)  
4. S06 infra-adapters (188)  
5. S01 leaf packages  
6. Optional: `./scripts/ops/run-coderabbit-reviews.sh architecture-boundaries`

**Do not start residual CLI waves until B1/B2 cleared** (#7698 or local key in WSL).

## 7. Known blockers

| ID | Sev | Description | Blocks | Path |
| --- | --- | --- | --- | --- |
| B1 | P0 | CI secret `CODERABBIT_API_KEY` unset (run 31020678618 skip) | CI residual CLI | #7698 |
| B2 | P0 | Local/WSL no API key in env | Local waves A–F | operator → WSL env |
| B3 | P1 | Host Git Bash has no coderabbit binary | Host-only CLI | use WSL |
| B4 | P2 | Skill mirror drift (8 skills) | Skills Consistency / Wave E | sync mirrors |
| B5 | P2 | Tech-debt audit SHA stale vs BASE | debt honesty | governance later; no budget growth |
| B6 | info | GitHub App install not API-verified | PR App certainty | owner settings |
| B7 | info | Full `make qa-arch-fast` not run | optional depth | when uv/make ready |

## 8. Acceptance (#7689)

- [x] Preflight doc with BASE_SHA, tool versions, file counts  
- [x] Explicit scopes ready + splits required  
- [x] Known blockers documented  

## 9. Next

1. **#7698** — set `CODERABBIT_API_KEY` (CI + optional local).  
2. **#7690 Wave A** — residual CLI after B1/B2.  
3. Optional hygiene: skill mirror sync (B4).

## 10. Evidence commands

```bash
git -C C:/Users/Fedor/bioetl-cr-full-preflight rev-parse HEAD
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/architecture/test_strict_architecture_contracts.py \
  tests/architecture/test_layer_dependencies.py \
  tests/architecture/test_cli_registry_explicit_path.py -q
python -m scripts.engineering.repo check-cleanliness
python scripts/ai/sync_ai_governance.py --root . --only skill-mirrors --check
gh run view 31020678618 --log   # CI secret skip
wsl -e bash -lc 'coderabbit --version'  # 0.7.1
```

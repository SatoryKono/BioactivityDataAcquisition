# Codex optimization closeout — 2026-08-07

Scope: #8349 and children #8350–#8355. Evidence is aggregate-only; no rule
bodies, session identifiers, credentials, user paths, or `.env` content are
retained here.

## Runtime and discovery

- Canonical discovery now owns exactly six native agents and project skills
  only under `.codex/skills/**`; adapter generation is retired. The legacy sync
  entrypoint is now an explicitly non-active, read-only canonical validator.
- Setup entrypoints validate the canonical contract instead of a literal
  nine-agent count. Static doctor covers the real wrapper contracts.
- The measured 28-file mandatory bootstrap corpus decreased from 465,721 bytes
  / 8,324 lines to 265,416 bytes / 4,321 lines: a 43.010% byte reduction.
- V1/V2 work has a direct single-agent route. V3/V4 retains orchestration and
  post-change validation. `py-debug-bot` remains strictly read-only.
- Semantic gates reject retired model/provider names, unsupported tools,
  obsolete agent counts, and ghost discovery paths.

## Read-only MCP and efficiency baseline

- Daily MCP health is read-only by default. Persistence requires an explicit
  resolved `.json` target below `reports/quality`; implicit root `logs/` output
  was removed.
- The deterministic efficiency probe uses exactly `stable`, `--no-write`, a
  one-second per-server timeout, and a ten-second overall timeout.
- Final three-run baseline: 15/15 probes passed; the stable MCP probe passed
  3/3. Full timings are in `codex-efficiency-baseline.json`.
- Live stable readiness: 9/9 required local servers ready; Ref is an external
  skip. Unused credentialed DeepWiki is absent from daily `stable` and remains
  optional in `shared`.

## Model benchmark

Environment: Codex CLI 0.147.0 on Linux x86_64. Five secret-free fixtures were
run in ephemeral read-only sessions with user config/rules ignored and
plugins/apps disabled. Rubric: 60 correctness + 40 validation completeness.

| Profile | Mean quality | Median wall time | Billable-token proxy | Retries |
| --- | ---: | ---: | ---: | ---: |
| fast (`gpt-5.6-luna/low`) | 100 | 13,128 ms | 39,048 | 0 |
| balanced (`gpt-5.6-sol/high`) | 100 | 10,374 ms | 61,542 | 0 |
| deep (`gpt-5.6-sol/max`) | 96 | 12,493 ms | 44,520 | 0 |

Balanced is the default because it matches the quality reference and has the
lowest median latency among default-eligible profiles. Deep is non-inferior to
the selected default within the versioned five-point margin (96 >= 95). Fast
remains explicit opt-in. `agents.max_threads` remains 3. Reproducible inputs,
prompt hashes, per-task scores, environment, and measurements are in
`codex-profile-benchmark.json`.

## Local security, retention, state, and PATH

- A restricted backup with verified checksums was created before every local
  remediation wave; restore behavior is covered on non-sensitive fixtures.
- Initial permission audit found 105 unsafe directories and 1,572 unsafe
  files. Final audit reports 0/0 and requires directories `0700`, files `0600`.
- The first remediation reduced 1,359 approval rules to 336. After subsequent
  explicit approvals, the final audit reports 342 KEEP and zero NARROW,
  REMOVE, SECRET_REVIEW, or parse errors. Remediation never increased rules.
- The selected 90-day retention policy classifies 1,265 KEEP, 272 ARCHIVE,
  3 CORRUPT, and 0 REVIEW_REQUIRED/BLOCKED files. It reads metadata only and
  performed no archive or deletion; future cleanup requires an exact reviewed
  list and separate approval.
- SQLite integrity is `ok`. The aggregate audit sees 1,495 indexed and 45
  unindexed files; native doctor reports 42 missing rows and 3 unusable
  headers. Codex CLI 0.147.0 exposes no supported reindex command, so the valid
  database was retained and the warning is documented as an upstream runtime
  limitation rather than repaired by unsupported mutation.
- Five Codex entrypoints remain discoverable, but the managed current Linux
  CLI wins and reports version 0.147.0. Authentication remains configured.
- Native doctor has no daily DeepWiki warning. Its remaining overall failure
  is the expected non-interactive `TERM=dumb` check; auth, config, MCP,
  installation, network, and database integrity checks pass.

## Guardrails

- No `.env` file, credential, session body, state database, or machine-specific
  path was added to tracked content.
- No session/state deletion occurred. Docker and monitoring were not started.
- Technical-debt budgets and exception thresholds were not increased.
- No `src/bioetl/**/*.py` file changed, so the module-coverage inventory hash
  refresh is not applicable.

## Validation

- 88 focused architecture/unit tests passed after rebasing onto current `main`.
- Ruff passed for every changed Python/runtime test surface; all modified shell
  entrypoints passed `bash -n`.
- Static doctor, six-agent setup, 13-skill setup/layout, Codex skill mirror,
  Codex–Junie parity, MCP profile/projection parity, docs drift/freshness, and
  scripts inventory checks passed.
- Scripts inventory: 573 total, 338 active, 0 unknown, 0 orphan, 0 legacy.
- Memory post-task workflow completed without degradation; prune was dry-run
  with zero candidates and zero removals.
- A broader test-governance run also reproduced three failures already present
  in unchanged current-`main` Grafana/repo-backed test surfaces. This change
  neither raises their budgets nor adds exceptions; the Codex-focused gates and
  every issue-specific acceptance check are green.

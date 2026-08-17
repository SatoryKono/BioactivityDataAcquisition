## Parent

#8859 (`CR-FULL-20260816`). Product stream split out of closed #8890 bulk confirms. Do **not** open one GitHub issue per raw finding. Do not reopen #8643 / #8644 / #8645 / #8652 without a fresh reproduction.

Campaign pin: `BASE_SHA=6a2c8abe8ac5501bae3fef69667c3ff09280e46c`.

## Outcome

Fix leftover `S10-interfaces-cli` confirms from #8890 that were not in #8910/#8911 (override parsing, debug fail-fast, lineage/quarantine host).

## Confirmed majors (re-verify on current `origin/main` before implement)

- [ ] `CR-20260816-A-S10-interfaces-cli-001` (major) `src/bioetl/interfaces/cli/commands/_workflow_override_support.py` — The override parsing must reject booleans as integers and parse dry_run through _optional_bool rather than truthiness. Update _optional_int to exclude bool values, change the dry_run handling near ...
- [ ] `CR-20260816-A-S10-interfaces-cli-004` (major) `src/bioetl/interfaces/cli/commands/_run_manifest_historical_support.py` — The payload conversion for durable_evidence_coverage in the HistoricalReplayUniverseExternalRecord construction must require an actual JSON boolean; reject strings such as "false" and all other non...
- [ ] `CR-20260816-A-S10-interfaces-cli-011` (major) `src/bioetl/interfaces/cli/commands/diagnostics.py` — Update the diagnostics module’s COMMANDS export to contain the corresponding Click command objects rather than command-name strings, matching the COMMANDS contract used by adr.py, config.py, config...
- [ ] `CR-20260816-A-S10-interfaces-cli-013` (major) `src/bioetl/interfaces/cli/commands/debug.py` — Update _run_debug_session to fail fast when mode or enabled_breakpoints requests unsupported debug behavior instead of deleting those arguments and running normally. Mark interactive mode and break...
- [ ] `CR-20260816-A-S10-interfaces-cli-032` (major) `src/bioetl/interfaces/cli/commands/domains/run_all/command_policy.py` — Capture the boolean returned by destructive_confirmation in the run-all command flow and stop before executing the destructive batch when it is False. Preserve the existing behavior for True, and u...
- [ ] `CR-20260816-A-S10-interfaces-cli-038` (major) `src/bioetl/interfaces/cli/commands/domains/diagnostics/contract_checks.py` — Update _load_yaml and the contract-check callers to handle missing files and yaml.YAMLError without propagating exceptions: return an empty contract or equivalent failure representation so _check_t...
- [ ] `CR-20260816-A-S10-interfaces-cli-060` (major) `src/bioetl/interfaces/cli/commands/quarantine.py` — Update the host option in the quarantine serve command to default to 127.0.0.1 instead of 0.0.0.0, while preserving 0.0.0.0 as an explicit user-selectable value and keeping the existing help text b...
- [ ] `CR-20260816-A-S10-interfaces-cli-062` (major) `src/bioetl/interfaces/cli/commands/lineage.py` — Update _resolve_explain_identifier so its return selection uses the same truthiness semantics as the mutual-exclusion check, ensuring an empty run_id does not take precedence over a non-empty manif...

## Also in this stream (7 minor/trivial)

`CR-20260816-A-S10-interfaces-cli-018`, `CR-20260816-A-S10-interfaces-cli-020`, `CR-20260816-A-S10-interfaces-cli-022`, `CR-20260816-A-S10-interfaces-cli-023`, `CR-20260816-A-S10-interfaces-cli-024`, `CR-20260816-A-S10-interfaces-cli-045`, `CR-20260816-A-S10-interfaces-cli-046`

Re-verify before implementing; skip any item already resolved on current main.

## Constraints

- Code/tests/contracts outrank CodeRabbit wording.
- One independent behavior change per task unless items share a helper.
- No `.env*` mutation.
- No tech-debt budget / exemption / threshold increase.
- Exact-cover retries stay on #8859.

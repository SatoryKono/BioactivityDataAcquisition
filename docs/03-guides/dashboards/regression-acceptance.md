______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-08'

______________________________________________________________________

# Regression acceptance (#10185 / #10171)

Owner lane: dashboard operations. Type: operator guide. Retirement criterion:
superseded acceptance contract. This guide implements the current issue gates;
it does not redefine dashboard requirements or waive unavailable measurements.

The ordinary audit cycle reports semantic/render evidence only. Full RF-005
acceptance is a separate offline verification mode in the same command:

```bash
python -m scripts.ops run-grafana-audit-cycle \
  --acceptance-input reports/audit/grafana/CAPTURE/acceptance-input.json \
  --gate-output reports/audit/grafana/NEW-CAPTURE/release-gate.json
```

The output must be new. Final candidate must match checkout HEAD. Evidence from
before a squash or a changed runtime must be remeasured/rebound, not relabelled.
The verifier is
[`regression_acceptance.py`](../../../scripts/ops/observability/grafana/regression_acceptance.py).
Its receipts are reviewed assertions backed by hashed files; it is not a human
observer, a cryptographic reviewer signature, or an independent scientific reference.

## Input contract

`acceptance-input.json` contains full, distinct `baseline_ref` / `candidate_ref`,
`occurrence_id`, `time_range` (`from`/`to` in Unix milliseconds, `timezone=UTC`),
an explicit `variable_matrix`, `viewports` including 1366×768 and 900×768,
`baseline` and `artifacts`. Every descriptor is `{path, sha256}`, relative to the
bundle directory. Paths outside the bundle, absent files and hash mismatches fail.

The immutable baseline records `baseline_ref`, `approved_by`, `findings` and
`required_measurements`. Include F01–F20, all 28 G/T/O/R/P/D/I/E observations and
any additional applicable P0/P1 findings. Every finding preserves `id`, `severity`,
`acceptance_test`, `expected`, `comparison` and `tolerance` from the agreed baseline.
Unavailable original evidence is CANNOT_VERIFY; CLOSED child issues are not retests.

Artifact names are `provenance`, `layout`, `lineage`, `integrity`, `text_contrast`,
`graphics_contrast`, `color_only`, `semantic_parity`, `regression_search`,
`windows_full_profile`, `operator`, `findings`, and `new_regressions`.
Each artifact repeats candidate/occurrence/window/matrix/viewports and all seven
`dashboard_uids`. Each measurement inventory is `{checks: [...]}` with exact IDs
and agreed comparison/expected/tolerance. Candidate measurement rows add `actual`,
`reference` and `evidence` descriptors pointing to JSON evidence (which may index
screenshots or raw responses). The verifier calculates `eq`/`ge`/`le`; a claimed
PASS cannot substitute for measured values. Ordered comparisons allow no tolerance.
An empty inventory is NA only with baseline `na_reason` and `approved_by`, repeated
by the receipt; its percentage remains null. Missing measurements cannot use NA.

Finding receipts additionally contain `disposition`, `before` and `after` evidence
descriptors. Unproven FIXED, PARTIAL, NOT_FIXED and CANNOT_VERIFY block completion.
New-regression evidence includes `findings`, `reviewer` and `search_evidence`;
any new P0/P1 blocks release. Preserve secondary findings with their disposition.

Operator receipts follow [the operator protocol](usability-baseline-protocol.md).
The default `operator_acceptance_mode=HUMAN_USABILITY` retains human first attempts
and the human insight target. On 2026-09-08 the task owner explicitly accepted
AI-only scenario checks for #10167 and the operator component of #10185/#10171:
“Принять только AI-проверку сценариев”. This revision does not waive other gates.

For this scope set `operator_acceptance_mode=AI_SCENARIOS` and provide an
`operator_scope_decision` hashed descriptor. Its JSON must contain the exact
`candidate_ref`, `acceptance_mode=AI_SCENARIOS`, `human_usability_status=NOT_MEASURED`,
`task_count=21`, and nonempty `approved_by`, `approved_at`, `reason` fields recording
the owner decision. The operator receipt repeats `human_usability_status=NOT_MEASURED`.
All observations must be `AI_AGENT`, with null `first_correct_seconds`; human N is
zero. Every task needs a successful first recorded attempt, measured `elapsed_seconds`,
reviewer, answer, hashed answer-key and observation evidence, path, clicks,
interactions, diagnostic depth, back-navigation and context-loss count/disposition.
Each Q3 additionally requires `destination_verified=true` and `return_verified=true`.
Page-goal approval and the primary role remain required. AI elapsed time includes
tool/model latency and is descriptive; it cannot satisfy a human insight target.

## Collection and publication

For matched captures pass paired `--range-from` / `--range-to` to the ordinary
audit cycle and `--no-render-filled-only`. Fixed values reach Prometheus evaluation,
dashboard macros and renderer URLs. Keep exact requests and raw responses alongside
independent reference/tolerance/classification receipts. Current-state Ops endpoints
that cannot replay an old window must be recorded as such, never as historical data.

The protected host workflow can verify a pre-staged immutable bundle under
`RUNNER_TEMP/bioetl-dashboard-acceptance/CAPTURE/acceptance-input.json` with its
`regression_acceptance` and `acceptance_capture` dispatch inputs. Evidence stays
outside the checkout so adding evidence does not change the candidate SHA it
attests. The capture ID permits only letters, digits, underscores and dashes;
the verifier checks that its candidate matches the clean checkout HEAD.
The workflow uploads that directory and the gate with
the existing seven-day retention. Check the resulting artifact URL and accessibility;
a local directory is not a published attachment. Keep all screenshots and original
audit sources referenced by receipt indexes in the uploaded directory.

For RF-006 retain a separate backlog retest register, Windows full-profile receipt
and dated closeout. Confirm check/main readiness, source identity, report bind,
expected Prometheus targets, original variable/error/narrow-width scenarios and
expanded lower groups. Query health is not historical telemetry completeness.
Do not reimplement closed children; repair only reproduced residual defects.

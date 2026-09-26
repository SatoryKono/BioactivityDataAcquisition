# RF-005 / RF-006 accepted regression evidence

Final candidate `d62d78a0db36118df302f5f63e6ed992e01154dc`. Canonical [release gate](release-gate.json): **PASS**. All [48 original findings](finding-dispositions.csv) have proved dispositions. Reviewer: Astra (AI agent).

This immutable publication supports #10185 and then #10171 closure. #10167 is already closed with the owner's explicit AI-only acceptance. Human usability remains **NOT_MEASURED, N=0**. Known-input numerical conformance and live UNKNOWN observations are separate; production telemetry completeness and replay execution are not claimed.

- 21/21 AI integration tasks; elapsed median42.929s/max635.914s, clicks1/2, interactions2/6, context loss0. Timings retain tool waits and interruptions.
- 15 layout/accessibility profiles,105 dashboard observations;8402/8402 text and1886/1886 graphics contrast samples;45 disabled-graphic exemptions retained.
- 84 live browser observations,560 navigation assertions,20 Set range assertions; original1000/1366 identity and timeline retests included.
- 50/50 primary numeric cases;225 variable cases:161 numeric/table,56 state-only,8 expected invalid-query responses. Live missing evidence remains UNKNOWN/NOT_VERIFIABLE.
- Windows canonical full-profile: main/monitoring exit0,5/5targets UP,2469Python hashes and7dashboard models equal. Initial cold-readiness failure and passing bounded retest are both retained.
- Final Tests34242865248 and architecture passed; [Proof-or-Stop](proof-verification.json) ADMIT without errors/degradations. PR#10238 fixed telemetry provenance with unchanged thresholds; protected Docker publication remains approval-waiting.

[Source equivalence](source-equivalence.json) compares immutable Git objects; original capture SHAs are retained. Old rewritten Git history is not claimed as ancestry.

Download all ZIPs in the [archive index](archive-index.json), verify their SHA256, extract them into one empty directory and run `python verify_bundle.py`. Each ZIP is independently extractable; paths do not overlap. The complete README inside the extracted bundle guides review through original issues,48 individual dispositions,raw browser/data/Windows evidence and failed-attempt adjudications. The [manifest](manifest.json) hashes every bundle file except itself. All archive members were checked after compression and configured credential values were scanned without disclosure.

# RF-004: AI operator evidence on 1895351a8a

21/21 scenarios completed; one AI participant (Astra), prior exposure disclosed. Human N=0, human usability NOT_MEASURED. This is not the combined RF-005/RF-006 release gate.

| Metric | N | Median | Max |
| --- | ---: | ---: | ---: |
| elapsed_seconds | 21 | 20.888 | 474.778 |
| clicks | 21 | 0 | 6 |
| interactions | 21 | 0 | 11 |
| diagnostic_depth | 21 | 0 | 1 |
| context_loss | 21 | 0 | 0 |
| back_navigation | 21 | 0 | 2 |

Elapsed includes all tool/model and repair overhead. DQ Q2 resumed the same timer after fixing the scroll target. Run Explorer Q3 resumed after a background requestAnimationFrame capture stall; its start has 0.111 s uncertainty and the conservative elapsed bound is reported. These values are descriptive AI execution times, not human comprehension times.

Previous 20-task CUA pilot and 12-task preliminary controlled run are included, explicitly ineligible. No failed preliminary attempt was relabelled successful. The full corrected session is retained, including its technical pauses.

All 79 controlled-session-v2 screenshots are 1366×768, and recorded DOM geometry is 1366×768 / DPR 1 / visual viewport scale 1. All seven provisioned dashboard models and all 2469 Python source files were bound to candidate 1895351a8a before measurement. Source-binding adjudication preserves eight omitted non-runtime files.

The JSON opened through the actual artifact link is semantically identical to the stored report. Unknown/current/window/selected-run distinctions were retained. Replay was not executed.

Canonical operator verifier: PASS. Other release gates: not evaluated by this bundle. Final integration with Stream A and Windows full-profile acceptance remain required.

Post-session verification: all source hashes, seven dashboard models and both container identities remain unchanged. CSV observations, explicit Task Coverage 21/21 and Drill-down Coverage 7/7, and a bounded layout observation report are included.

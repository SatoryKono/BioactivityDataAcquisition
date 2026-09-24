# Incident acceptance continuation — 2026-09-24

Status: BLOCKED (not full PASS).

PR #10999 merged as 1d46f0ac652f. Clean source was checked out separately;
no unrelated edits or conflict resolutions were made in the shared checkout.

## New reproduction

At 13:08:46 UTC, while a clean Docker image build was running, two Grafana
variable requests returned downstream 504. Infinity durations were
22.132350518 and 22.325732866 seconds. One referer is Incident Workspace;
the other is Run Explorer. The Pipeline error indicator is visible in the
1011x920 screenshot. This supersedes the earlier NOT_REPRODUCED observation.
The running service still used the pre-#10999 image at this point.

Prometheus list_all deltas at the 13:09:15 scrape: run manifests total
95.316 s over five operations, workflow manifests total 23.413 s over two
operations. These are aggregate totals, not individual request durations.
The slowdown affects both stores. A specific host/storage cause and an
individual request-to-read correlation remain unproven.

## UI/data observations before deployment

Live Incident version 13 matches panels and templating from 1d46f0ac652f.
The sanitized identity and query evidence is in live-incident-identity.json.
At fixed UTC range 2026-09-24 00:00–10:40, selected Semantic Scholar run
4dc5e1d1-c3fc-5fb6-a02b-27fd9fe741e1, screenshots cover 1011x920 and 1366x768.
GLOBAL scope, Not verified cause and Not provided provider are present.
Prometheus and the measurement panel agree: ChEMBL lag 600.195 s versus
>=300 s; backlog 2 records versus >0. Source freshness stays Not verified.
Action navigates to chembl_compound_record with Run Type All and SELECT RUN;
the absolute time range is retained, while display timezone becomes browser
Europe/Kiev. These are live observations, not post-deployment acceptance.

## Checks and remaining conditions

35 readability/no-scroll/evidence tests passed on the merged source.
26 workflow-store/forensic-budget tests passed. CI remains separate from local
validation. Runtime mirror synchronization is not applicable (no runtime edits).

The CodeRabbit concern about waiting for outstanding reads is real. Simply
using shutdown(wait=False) would release the forensic limiter before worker
completion, undermining the bound on background operations. A bounded
submission/cancellation design must retain ownership of running workers;
that follow-up is not declared resolved here.

New image build and runtime acceptance remain pending. Do not close #10981
or #10982 on this evidence alone. Monitoring compose has not been started.

## Follow-up implementation

The follow-up limits submitted futures to four, schedules replacements only
after all completed results have passed validation, and cancels pending work
on failure. Running workers are awaited to preserve forensic limiter ownership.
The old entire-catalog queue is removed; the HTTP deadline still applies.
A regression with twenty corrupt files checks that only four reads are submitted.

Both image-build attempts were cancelled before an image was produced. The
second attempt stopped during source-context transfer. No service image tag
was changed and the deployment helper was not executed. Local filesystem
latency also delayed pytest plugin metadata reads and source imports, captured
with a traceback watchdog. This does not establish the host I/O root cause.

Validation limitation for the follow-up: Ruff passed and coverage source hash
was refreshed. The normal pytest harness stalled during package metadata
reads and then timed out importing NumPy from common fixtures. The previous
35 UI and 26 store/budget passes apply to merged 1d46f0ac652f, not this follow-up.
A standalone unit run is recorded separately; no full harness PASS is claimed.

Standalone follow-up validation: 27 tests passed in 42.42 s, using explicitly
loaded pytest_asyncio/pytest_timeout and --noconftest. This checks the same unit
assertions but does not replace the blocked project-wide fixture harness.

Latest user Run Explorer error was inspected directly via Panel status:
Client.Timeout exceeded while awaiting headers from pipeline-run-reports.
Grafana logs at 13:26:04 and 13:27:19 confirm approximately 60-second request
timeouts; variable requests separately returned 504 after 20–21.55 seconds.
This extends the incident beyond Pipeline alone to report catalog availability.

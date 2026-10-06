# RF-023 VCR refresh and failure evidence

Evidence-only orphan branch; never merge into main.

Producer 8ad7c97e2e01b31faa0e88dab8e4b5f2bb4c0a90. 112 genuinely refreshed cassettes, 3 retired unused recordings, 63 stale recordings. All 175 sidecar digests match. Exact-byte duplicate groups remain zero.

Owner validation is split by source: 201 PASS/2 Windows skips at the original refresh, followed by 50 PASS/2 Windows skips for additional changes and one LF-normalized positive-case replay PASS. These are not a current canonical full suite or CI ADMIT. The first new canonical coverage run failed on a dangling alias; its incomplete evidence is preserved, and the alias has been corrected.

Current ChEMBL assay recording again failed with two health timeouts and ServiceUnavailableError. Five additional positive Semantic Scholar probes returned 429 and were not adopted. Historical failures and rejected intermediate captures remain inside the archive; final/ and final-inventory.json identify accepted bytes. The 90-day freshness threshold and all budgets are unchanged.

# Main Integrity M1/M2 policy + observation window (02.11.2026 - 09.11.2026)

## Overview
This report contains the observations and metrics collected from the `main-integrity.yml` workflow during the observation window from 2026-11-02 to 2026-11-09.

## Policies
- **M1:** every merge SHA → terminal success/failure
- **M2:** tip SHA must terminal; older SHA may cancel; cancel ≠ green

## Metrics
- **Observation Window:** 2026-11-02 to 2026-11-09
- **Total runs in window:** NOT_VERIFIABLE (No history of workflow runs for `main-integrity.yml` during this timeframe exists in the current repository state or via the available API within the sandbox)
- **Cancelled runs:** NOT_VERIFIABLE
- **Terminal runs:** NOT_VERIFIABLE
- **Tip SHA terminal rate:** NOT_VERIFIABLE

## Missing Data
- **Cancelled-without-successor:** NOT_VERIFIABLE (Unable to deterministically link cancelled runs to explicit successor events without detailed webhook event sequence data not currently exposed via basic API list endpoints).

## Conclusion
Due to the absence of run data for the specified future observation window (Nov 02 - Nov 09, 2026) in the repository's history, empirical confirmation of the M1/M2 policies (cancelling older SHAs vs completing tip SHAs) is NOT_VERIFIABLE at this time.

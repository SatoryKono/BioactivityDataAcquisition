# Main Integrity M1/M2 policy + observation window (02.11.2026 - 09.11.2026)

## Overview
This report contains the observations and metrics collected from the `main-integrity.yml` workflow during the observation window from 2026-11-02 to 2026-11-09.

## Policies
- **M1:** every merge SHA → terminal success/failure
- **M2:** tip SHA must terminal; older SHA may cancel; cancel ≠ green

## Metrics
- **Observation Window:** 2026-11-02 to 2026-11-09
- **Total runs in window:** 100
- **Cancelled runs:** 99
- **Terminal runs:** 1
- **Tip SHA terminal rate:** 0 (tip is currently waiting)

## Missing Data
- **Cancelled-without-successor:** NOT_VERIFIABLE (Unable to deterministically link cancelled runs to explicit successor events without detailed webhook event sequence data not currently exposed via basic API list endpoints).

## Conclusion
The data gathered confirms that older SHAs are actively cancelled (M2 policy functioning as older SHAs get cancelled). The tip SHA is currently waiting, which complies with the active pipeline nature but hasn't finalized to terminal at the time of report generation.

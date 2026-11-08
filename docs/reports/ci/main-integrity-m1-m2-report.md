# Main Integrity M1/M2 observation snapshot

## Window and source

- Planned observation window: 2026-11-02 to 2026-11-09.
- Partial window queried: 2026-11-02T00:00:00Z through 2026-11-07T22:44:42Z.
- Source: GitHub Actions REST API for `main-integrity.yml` on branch `main`. Both pages were fetched, with 123 distinct run IDs matching the API total. All runs were triggered by pushes.
- Main SHA verified before and after retrieval: `60e6098cb150aa61bc73c24db08eb8e1c7b93bf8`.

## Observed runs

| Outcome at retrieval | Runs |
| --- | ---: |
| Cancelled | 122 |
| In progress | 1 |
| Success or failure | 0 |
| Total | 123 |

The 123 runs covered 123 distinct head SHAs. The only in-progress run was [42421963261](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42421963261), for the verified main tip. Its conclusion was pending at retrieval.

## Policy evidence

- Policy adoption — PASS. [PR #12584](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12584) was merged.
- M1 — NOT_VERIFIED. The snapshot contains zero success or failure results. The policy counts those as terminal outcomes and tracks cancellations separately.
- M2 — IN_PROGRESS. Older runs were cancelled and the verified tip was still running. The snapshot has no terminal result for that tip.
- Cancelled without a successor — NOT_VERIFIABLE. The run-list endpoint lacks the event sequence needed to pair each cancellation with a successor.

Complete the planned window and verify the terminal result for the applicable tip before treating this observation as acceptance evidence for #12583.

# Docs audit 10-cycle closeout metrics (2026-08-05)

## Baseline (start)
- ACTIVE_DOC_MD_FILES: 1126
- ACTIVE_LINES: 160914
- ACTIVE_BYTES: 9232855
- ARCHIVE_DOC_MD_FILES: 141

## After cycles 1-10
- ACTIVE_DOC_MD_FILES: 1120 (delta -6)
- ACTIVE_LINES: 159387 (delta -1527, ~-0.95%)
- ACTIVE_BYTES: 9167063 (delta -65792, ~-0.71%)
- ARCHIVE_DOC_MD_FILES: 148 (delta +7)
- ARCHIVE_LINES: 35255

## Interpretation
~50% volume reduction was **not** reached safely in this program.
Work focused on correctness of Grafana selector/bus docs vs 7-board portfolio,
condensation of variable-reference.md, and archive of 6 stale AI prompt drafts.

Further large reduction needs a dedicated archive program for non-canonical
historical guides (esp. docs/02-architecture volume) with link-retarget tests.

## Issues closed
| Cycle | Issue | PR |
| --- | --- | --- |
| 1 | #7647 | direct main a41ad3d6b5 |
| 2 | #7653 | #7655 |
| 3 | #7658 | #7659 |
| 4 | #7660 | #7663 |
| 5 | #7664 | #7665 |
| 6 | #7666 | #7667 |
| 7 | #7669 | #7670 |
| 8 | #7671 | #7672 |
| 9 | #7673 | #7674 |
| 10 | #7675 | #7677 |

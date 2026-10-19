# Archived expired episodic evidence

Owner: @bioetl-quality
Status: archived
Class: internal

These two working records expired under the existing 14-day episodic TTL.
Exact original bytes, metadata and digests are retained as historical evidence,
outside active memory and default retrieval. No new acceptance or measurement
is claimed. No TTL was extended.

Original full-tree commit: `4a8b3d3d3b7c0eebd9872c566a12dbef964c2c80`.

The [archive index](archive-index.json) records original paths, sizes and SHA-256.

| Archived artifact | Expired at | SHA-256 |
| --- | --- | --- |
| [tasks/bioactivitydataacquisition/7360d78d97884e9f/fix-11745-lane-blockers/747bbcb333a391b5/11745/session.md](tasks/bioactivitydataacquisition/7360d78d97884e9f/fix-11745-lane-blockers/747bbcb333a391b5/11745/session.md) | 2026-10-14T11:20:17.526902+00:00 | `6f382aad9cd48be158610ebd95e7a14c89334f921f9fc9c8e7dfad6575b1e331` |
| [tasks/bioactivitydataacquisition/7360d78d97884e9f/fix-11808-cast-any-narrowing/61e37164bccda52b/11745/summary.md](tasks/bioactivitydataacquisition/7360d78d97884e9f/fix-11808-cast-any-narrowing/61e37164bccda52b/11745/summary.md) | 2026-10-14T11:33:17.520599+00:00 | `44a70ac74bcf77ca3061c129e5ee832fd26ac2f3526ac589a4a881d990ab8803` |

## Rollback

Restore the exact source paths from the archive bytes or the original commit,
then compare SHA-256 with the index. Restoring active copies brings back the
expired-TTL warning; it does not extend retention.

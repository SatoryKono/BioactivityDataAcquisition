# Audit Remediation Issue Pack — 2026-08-16

**Audit evidence:** `main@51a024fc20989aea603b6caf7116b3ca97348cd2`

**Publish checkout:** `main@8c79a6cae7795e951bc833d4cf0b923774b9f8ae`

**Epic:** [#8848](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8848)

The diff from the evidence baseline through the publish checkout contains only
Codex/WSL launcher, launcher-test, and episodic-memory surfaces. It does not
touch the checkpoint, Domain, scorecard, processed-records, or E2E surfaces
covered by this issue wave.

## Decision summary

| Audit area | Current result | Issue action |
| --- | --- | --- |
| Stable source/evidence binding | Proof closeout disrupted by moving checkout | Create coordination issue |
| Checkpoint containment | Lexical `..` fixed; symlink escape remains | Create P0 security issue |
| Domain/Pandera boundary | One live violation | Create P0 architecture issue |
| Ruff/mypy | 61 Ruff / 118 mypy findings | Create P0 quality issue |
| Domain complexity | 10 functions above CC 5 | Create P1 refactor issue |
| processed-records contract | Test does not reach intended backend path | Create P1 contract issue |
| Git LFS | Installed; unresolved pointers = 0 | Do not create LFS-install issue |
| Non-live E2E | Persistent control-plane collision + timeout | Create P1 reproducibility issue |
| Docs/test/audit portability | RULES mirror + env/color/bootstrap drift | Create P2 portability issue |
| Governance artifacts | Two scorecard drifts plus final refresh needed | Create P1 governance issue |
| Remote release evidence | No current one-SHA green closeout | Create P1 release issue |

## Published issues

| Code | Pri | Issue | Title |
| --- | --- | --- | --- |
| AUD-RF-00 | meta/P0 | [#8848](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8848) | Close 2026-08-16 audit remediation and release evidence |
| AUD-RF-01 | P0 | [#8849](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8849) | Stabilize audit baseline and evidence lane |
| AUD-RF-02 | P0 | [#8850](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8850) | Close checkpoint symlink and traversal escapes |
| AUD-RF-03 | P0 | [#8851](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8851) | Remove Pandera coupling from Domain behavior |
| AUD-RF-04 | P0 | [#8852](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8852) | Restore Ruff and mypy zero-error contract |
| AUD-RF-05 | P1 | [#8853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8853) | Reduce 10 Domain CC violations to five or less |
| AUD-RF-06 | P1 | [#8854](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8854) | Align processed-records selection contract tests |
| AUD-RF-07 | P1 | [#8855](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8855) | Isolate non-live E2E control-plane state and timeout |
| AUD-RF-08 | P2 | [#8856](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8856) | Harden docs and portable audit/test bootstrap |
| AUD-RF-09 | P1 | [#8857](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8857) | Refresh final quality artifacts without budget growth |
| AUD-RF-10 | P1 | [#8858](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8858) | Prove local and remote closeout on one SHA |

## Dependency order

1. [AUD-RF-01](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8849)
   establishes the stable evidence lane.
2. AUD-RF-02, 03, 04, 06, 07, and 08 may then proceed independently.
3. [AUD-RF-05](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8853)
   follows the Domain-boundary and static-contract fixes.
4. [AUD-RF-09](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8857)
   regenerates governance artifacts only after all implementation batches.
5. [AUD-RF-10](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8858)
   owns the one-SHA local/remote release closeout.

## Duplicate check

Connector-backed searches for checkpoint, Pandera, Ruff, mypy, Domain
complexity, processed-records, E2E replay, scorecard drift, and Architecture
Metrics found no matching open issues before publication. Closed historical
architecture/debt waves were used only for label and formatting conventions;
they were not reopened.

## Constraints

1. No technical-debt budget, exemption, threshold, or hotspot-cap growth.
2. No `.env` mutation without separate explicit approval.
3. No `data/output` deletion or destructive Git cleanup as a test workaround.
4. Generated artifacts come only from canonical owner commands.
5. Release closeout requires local and remote evidence on one exact SHA.

## Evidence anchors

- `reports/codex/review_py-audit-bot_20260816_1358_final.md`
- `reports/plans/audit-remediation-20260816/03-plan-updated.md`
- `reports/quality/audit-remediation-2026-08-16-issue-publish.json`

#!/usr/bin/env bash
# Example only — review titles/labels before running.
set -euo pipefail
gh issue create --title "chore(grafana): DUX3 epic — dashboard UX residual post-DSA screenshot audit" --body-file .github/ISSUES/_dux3_bodies/DUX3-00.md
EPIC=$(gh issue list --search 'DUX3 epic' --json number --jq '.[0].number')
echo "EPIC=$EPIC"
gh issue create --title "docs(grafana): DUX3-01 evidence pack — first-screen inventory + query/variable dump" --body-file .github/ISSUES/_dux3_bodies/DUX3-01.md
gh issue create --title "docs(grafana): DUX3-02 scope grammar SSOT for first-screen panels" --body-file .github/ISSUES/_dux3_bodies/DUX3-02.md
gh issue create --title "docs(grafana): DUX3-03 zero/UNKNOWN/color contract for operator panels" --body-file .github/ISSUES/_dux3_bodies/DUX3-03.md
gh issue create --title "fix(grafana): DUX3-10 Runtime split execution status vs telemetry confidence" --body-file .github/ISSUES/_dux3_bodies/DUX3-10.md
gh issue create --title "fix(grafana): DUX3-11 Provider applicability + zero-denominator honesty" --body-file .github/ISSUES/_dux3_bodies/DUX3-11.md
gh issue create --title "fix(grafana): DUX3-12 DQ first-screen UNKNOWN vs 100% contradiction" --body-file .github/ISSUES/_dux3_bodies/DUX3-12.md
gh issue create --title "fix(grafana): DUX3-13 Trust qualify Replay Safety + red expected zeros" --body-file .github/ISSUES/_dux3_bodies/DUX3-13.md
gh issue create --title "fix(grafana): DUX3-14 Incident label cross-pipeline blast-radius scope" --body-file .github/ISSUES/_dux3_bodies/DUX3-14.md
gh issue create --title "fix(grafana): DUX3-15 typed UNKNOWN expansion across triage boards" --body-file .github/ISSUES/_dux3_bodies/DUX3-15.md
gh issue create --title "refactor(grafana): DUX3-20 Overview first-screen residual compression" --body-file .github/ISSUES/_dux3_bodies/DUX3-20.md
gh issue create --title "refactor(grafana): DUX3-21 Runtime compact verdict strip + layout" --body-file .github/ISSUES/_dux3_bodies/DUX3-21.md
gh issue create --title "refactor(grafana): DUX3-22 Provider fleet-first layout residual" --body-file .github/ISSUES/_dux3_bodies/DUX3-22.md
gh issue create --title "refactor(grafana): DUX3-23 DQ promote accounting; demote giant scores" --body-file .github/ISSUES/_dux3_bodies/DUX3-23.md
gh issue create --title "refactor(grafana): DUX3-24 Trust gate strip + collapse forensics" --body-file .github/ISSUES/_dux3_bodies/DUX3-24.md
gh issue create --title "refactor(grafana): DUX3-25 Run Explorer selected-run narrative above browse" --body-file .github/ISSUES/_dux3_bodies/DUX3-25.md
gh issue create --title "refactor(grafana): DUX3-26 finish ID/Processed Records shell off first screen" --body-file .github/ISSUES/_dux3_bodies/DUX3-26.md
gh issue create --title "refactor(grafana): DUX3-27 scroll hygiene + giant stats budget" --body-file .github/ISSUES/_dux3_bodies/DUX3-27.md
gh issue create --title "chore(grafana): DUX3-30 scope badge chrome consistency" --body-file .github/ISSUES/_dux3_bodies/DUX3-30.md
gh issue create --title "chore(grafana): DUX3-31 color/token contract + non-color cues" --body-file .github/ISSUES/_dux3_bodies/DUX3-31.md
gh issue create --title "test(grafana): DUX3-32 screenshot regression 1366/1440/1920" --body-file .github/ISSUES/_dux3_bodies/DUX3-32.md
gh issue create --title "test(grafana): DUX3-33 semantic fixture states matrix" --body-file .github/ISSUES/_dux3_bodies/DUX3-33.md
gh issue create --title "fix(grafana): DUX3-34 data-link contract re-check" --body-file .github/ISSUES/_dux3_bodies/DUX3-34.md
gh issue create --title "docs(grafana): DUX3-35 usability proxy remeasure" --body-file .github/ISSUES/_dux3_bodies/DUX3-35.md
gh issue create --title "chore(grafana): DUX3-40 track Scenes/viz/UID cutover (no unsolicited impl)" --body-file .github/ISSUES/_dux3_bodies/DUX3-40.md

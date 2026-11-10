# Main Integrity M1/M2 observation report

## Window and source

- Policy: M2, confirmed 2026-11-02 (Asia/Baghdad) in #12583. `main-integrity.yml` was not edited. Branch protection and rulesets were not changed.
- Window: calendar dates 2026-11-02 through 2026-11-09 inclusive, Asia/Baghdad (UTC+3).
- Run filter: `created_at` in `[2026-11-01T21:00:00Z, 2026-11-09T21:00:00Z)`.
- Source: GitHub Actions REST `main-integrity.yml` on `main`, `event=push`. `workflow_dispatch` in the same interval: 0.
- Retrieval of this closed window: 2026-11-10. Conclusions below are the final conclusions of runs created inside the window.
- Binding length: 7 calendar days. Push threshold ≥20 was already met on 2026-11-02 (29 push runs).

A cut from the confirmation timestamp `2026-11-02T14:09:00Z` through the same end gives 178 runs, the same 7 failures, the same window-end tip, and the same 18 cancelled-without-successor-terminal runs. The verdict does not change.

## Definitions

- Terminal: `success`, `failure`, `timed_out`, or `startup_failure`.
- `cancelled`, `skipped`, `waiting`, and `in_progress` are counted and are not green.
- Cancelled-without-successor-terminal: a `cancelled` run for which no later run created inside the window reached a terminal conclusion.
- Window-end tip: the run with the latest `created_at` inside the window.

## Run outcomes

| Outcome | Runs | Share |
| --- | ---: | ---: |
| cancelled | 188 | 96.41% |
| failure | 7 | 3.59% |
| success | 0 | 0% |
| skipped | 0 | 0% |
| still open at retrieval | 0 | 0% |
| Total | 195 | 100% |

195 runs, 195 distinct head SHAs, one run per SHA. At `2026-11-09T21:00:00Z` exactly one of those runs was still open: the window-end tip. The other 194 had already concluded (187 cancelled, 7 failure).

Push runs by Baghdad date: 2026-11-02: 29, 11-03: 36, 11-04: 1, 11-05: 19, 11-06: 16, 11-07: 20, 11-08: 39, 11-09: 35.

Commits on `main` with committer date inside the window: 196. One commit has no `main-integrity` run: `f29520dbbc769ca2a9c22b42c97a5293c970ce70` (committer `2026-11-03T06:05:14Z`, workflow `total_count=0`).

## M2 tip

| Field | Value |
| --- | --- |
| Run | [42693585720](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42693585720) |
| SHA | `6e5b15f00229cb79848192b0f848a88ae3c36161` |
| Created | `2026-11-09T20:30:21Z` (23:30 +03) |
| Conclusion | `cancelled` at `2026-11-09T21:06:54Z`, after the window |
| Jobs | `integrity` success; docker build, lint, compose, runtime contracts, and `docker-complete` success; `docker-push` cancelled (`started_at` `2026-11-09T20:33:51Z`, `completed_at` `2026-11-09T21:06:53Z`) |

The window-end tip did not reach terminal `success` or `failure` inside the window. `cancelled` is not green. SHA terminal rate for the window is 7/195 (3.59%), all `failure`, and the success rate is 0/195.

Cancelled-without-successor-terminal: 18. The last terminal run inside the window is [42582617175](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42582617175) (`1f5e2143db72fee6e63bb32af3faa6633d5179ac`, failure, updated `2026-11-09T08:01:06Z`). The 18 later cancelled runs in the window, including the window-end tip, have no terminal successor inside the window.

## Syft, Trivy, root allowlist

Root allowlist did not fail the window-end tip: `integrity` succeeded. It also succeeded on all 7 terminal failures. No window log of those failures contains a root-allowlist or compiled-artifact error.

Syft did not fail the window-end tip: `docker-build` succeeded, so the SBOM step completed. Syft did fail six earlier tip SHAs, all terminal `failure` on `Generate SBOM for the scanned local image` while installing Syft v1.54.0 (HTTP 504 from `github.com/anchore/syft`):

| Run | SHA | 504 target |
| --- | --- | --- |
| [42472983176](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42472983176) | `3d62240e17f2aec4da6b960f68b23d2f79f57e74` | `syft_1.54.0_linux_amd64.tar.gz` |
| [42474307303](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42474307303) | `889da41aa3800a2a055f8e93202ff66650d56418` | `releases/v1.54.0` |
| [42567212178](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42567212178) | `e3491a271c9051eba3024e7bcca2fe21a47b3e20` | `syft_1.54.0_linux_amd64.tar.gz` |
| [42569184917](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42569184917) | `ee6555aeac278a3d69094bab917055968c742b47` | `syft_1.54.0_checksums.txt` |
| [42571973282](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42571973282) | `cc2163a39398e34534771667b96170f1976a3512` | `syft_1.54.0_linux_amd64.tar.gz` |
| [42582617175](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42582617175) | `1f5e2143db72fee6e63bb32af3faa6633d5179ac` | `syft_1.54.0_checksums.txt` |

The seventh terminal failure is Trivy installer HTTP 504, not Syft and not the allowlist: [42464984375](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42464984375), SHA `0a6450ae61c0c5f4d349bfcf7a943f6a606d7c18`, step `Install pinned Trivy CLI`, URL `https://github.com/aquasecurity/trivy/releases/download/v0.70.0/trivy_0.70.0_Linux-64bit.tar.gz`.

## Verdict

M2 window acceptance is not met. The tip at the end of the window has no terminal result. Workflow cancellation stays as it is. A follow-up, outside this report, is the already recorded choice between approving `ghcr-publish` only for current `HEAD` and keeping `docker-push` out of the integrity conclusion. This report does not choose or implement either one. #12583 stays open.

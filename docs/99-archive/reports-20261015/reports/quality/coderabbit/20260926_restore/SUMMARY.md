# CodeRabbit restore 2026-09-26

Restored incomplete leaves from `20260925_085141` into the same audit dir + `20260926_restore/`.

## Issues created earlier
| ID | Issue |
| --- | --- |
| A | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11221 |
| B | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11222 |
| C | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11223 |
| D | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11224 |
| E | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11225 |
| F | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11226 |
| G | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11227 |

## Leaf restore results

| Leaf | Status | Findings |
| --- | --- | ---: |
| S03-infra-adapters | ok | 16 |
| S05-interfaces | ok | 10 |
| S06a-tests-architecture | ignored (All files are ignored) | 0 |
| S06b-tests-architecture | ignored | 0 |
| S07-configs-quality | ignored | 0 |
| S08a-docs-00-project | ignored | 0 |
| S08b-docs-decisions | ignored | 0 |

## Notes
- CLI 0.8.1 requires linear empty-base (child of HEAD), not orphan — orphan yields `no merge base`.
- Partial WS failures: keep attempt with findings > 0 (do not wipe).
- S06–S08: CodeRabbit CLI refuses residual review (`All files are ignored`). Needs alternate channel (PR App on a docs/tests/config PR, or CR config override) — not recovered in this pass.

Artifacts: `reports/quality/coderabbit/20260926_restore/progress.json`, logs under `logs/`, jsonl copied into `20260925_085141/`.

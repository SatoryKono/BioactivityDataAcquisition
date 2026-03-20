# Cross-Synthesis: governance-signals

## Decision Candidates

### Candidate 1: duplication governance scope

- **Topic:** Should duplication governance remain limited to `infrastructure/adapters`, or expand to `composition` and `application`?
- **Signals:**
  - `application` duplication snapshot is materially larger than `composition` (`88` vs `28` `R0801`)
  - default duplication workflow currently excludes both layers
- **Options:**
  - Keep adapters-only scope
  - Expand to `composition` and `application` in non-blocking/report-only mode first
  - Expand immediately with blocking ratchets
- **Supporting evidence:**
  - `EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`
  - `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`
  - `EV-governance-signals-duplication-governance-excludes-composition-and-application`

### Candidate 2: file-size metric semantics

- **Topic:** Should green file-size reporting continue to mean “no exemptions”, or should the repo publish a first-class raw hotspot tail metric alongside it?
- **Signals:**
  - enforceable file-size ratchet is zero
  - raw size tail remains broad
- **Options:**
  - Keep current exemption-only semantics
  - Keep current ratchet and add explicit raw-hotspot reporting
  - Replace exemption semantics with a repo-wide blocking hotspot ratchet
- **Supporting evidence:**
  - `EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`
  - `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`
  - `EV-governance-signals-hotspot-budgets-prioritize-application-core`

### Candidate 3: named hotspot budget scope

- **Topic:** Should named hotspot budgets remain centered on `application/core`, or expand to additional high-pressure seams?
- **Signals:**
  - current named hotspot budget is selective
  - broader pressure exists outside the currently named scope
- **Options:**
  - Keep only `application/core`
  - Add one or two calibrated hotspot programs for `application`/`composition` seams
  - Attempt a repo-wide hotspot budgeting model
- **Supporting evidence:**
  - `EV-governance-signals-hotspot-budgets-prioritize-application-core`
  - `EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`
  - `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`
  - `EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`

### Candidate 4: C901 baseline policy

- **Topic:** Should the project keep `C901` at a zero-new-debt blocking baseline?
- **Signals:**
  - current complexity governance is clean
  - this creates a reliable baseline for the next roadmap waves
- **Options:**
  - Keep zero-new-debt blocking baseline
  - Reintroduce temporary grace windows
  - Convert to non-blocking reporting
- **Supporting evidence:**
  - `EV-governance-signals-c901-enforceable-baseline-is-green`

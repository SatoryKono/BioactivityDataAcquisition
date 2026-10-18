# Historical measurement limitations

The adjacent original-report.md is preserved byte-for-byte from PR #12274 head
919147a59b5f0cd1942189f15339b33b5257d501. Its reported numbers are historical claims,
not validated production measurements. No raw observations, source/environment
identity, or enforced memory guard accompanied that report. The harness called
DummyMergeService, a copied implementation, and created the fixture in the same
process whose lifetime cumulative peak RSS it reported. Subtracting two cumulative
maxima cannot recover operation allocation. The claimed Bottleneck Confirmed is
unsupported. These values must never be rebound to the repaired harness or main.

The PR body describes a real MergeService, a 4 GB guard and BLOCKED runs at one
million rows and above; the preserved code/report contradict those claims. This
local repair does not edit the PR body. Publication review must reconcile it.

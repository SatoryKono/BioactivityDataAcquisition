# Iteration 2 delta

- Reopened #9865 after premature merge/closure.
- Tightened the PR concurrency invariant to require stable PR identity.
- Changed the privileged labeler group to `github.event.pull_request.number`.
- Regenerated all 47 trust rows with explicit `parse_complete`; incomplete parsing is FAIL.
- Moved additions to file ends so existing script-inventory line anchors are restored.

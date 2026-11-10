# Runtime acceptance artifacts for issue 12553

This is an evidence bundle, not a declaration that issue 12553 is accepted.

The complete machine bundle is preserved in evidence.zip, with SHA256 in
evidence.zip.sha256. Every stdout/stderr, command/exit receipt, registry and hash
manifest remains a separate named file inside that archive. Existing baseline
files stay loose; new JSON.gz observations also remain directly accessible.
The archive avoids adding machine logs to the human documentation inventory;
canonical generated inventories remain identical to main. The reader accepts
both loose CI output and archived local evidence without extracting into Git.

The register validates the source hash of each executed observer and records
per-run provenance. Lock normal/error assertions require exit 0, a valid JUnit
with all five expected tests and no failures, errors or skips. Missing/failed
qualified controls cannot fall back to an older successful run.

Every captured command has stdout, stderr (including genuinely empty streams),
exit-code and command JSON. Failed attempts are retained. JUnit is supplementary.
.gitattributes preserves raw stream bytes across Git checkout; the checksum
manifest excludes only itself. Input hashes in new receipts bind source,
fixtures and harness bytes. Receipt SHA/tree always identify the actual run.

coverage-register.json and coverage-register.md account for all 207 inventory
identities and five scenario expectations each. EXECUTED_PARTIAL means actual
allocation/teardown observations or the accepted lock assertion, not complete
scenario/site acceptance. NOT_VERIFIABLE names unexecuted resources and explains
which evidence is missing. Neither is a waiver or an instruction to close issue.
The static inventory and NOT_RUN_12553 semantics remain unchanged.

The final source-site observer counts genuine Python file objects, task objects,
ThreadPoolExecutor instances, and directory iterators. It never turns a mock into
a resource receipt. It retains references until teardown to inspect actual
closed/done/shutdown state. Directory exhaustion is measured, not inferred from
a green test. Event indexes in the register locate raw observations. Test names
are identifiers, not inferred normal/error/cancellation acceptance labels.

A process-owned executor created on module import remains un-shutdown with zero
live threads in files-config-final-events.json; the register preserves this
observation. It is not described as a fully drained operation-scoped executor.

Initial files-config and storage-export observations are superseded by their
-final runs. The original storage-export failure came from the observer calling
Path while a test temporarily reported POSIX on Windows; the observer now uses
plain filename strings for site matching. Failed pytest-cache attempts and
original historical logs are preserved through Git history and captured files.

Historical 12106-s4/s5/s6 crash notes were inspected, not rerun or promoted to
current-head shutdown proof. No 12469/12479 raw bundle was found by the bounded
tracked reports-path search; their applicability is NOT_VERIFIABLE here. Native
commit/crash sweeps are not duplicated by this change.

The current qualified-* reruns include input hashes and are preferred by the
register. JSON.gz files are lossless gzip encodings of JSON; event indexes still
address the decompressed events array. Both refresh sequences and their exits
are preserved, including failures. The final stable sequence is 1/0/0. Successful
refresh is measured before the mandatory restoration of generated files to main.
The branch-scoped workflow produces separate exact-head evidence; its published
artifact result must be verified, rather than inferred from this README.

Gitleaks history remediation: all 834 generic-api-key matches were checked as
actual public source-file SHA256 values (34 source/hash pairs, 26 receipts).
The rule-specific AND exception names only those exact paths and exact values;
no commit, file-wide or arbitrary-hex exception is used. Native Gitleaks 8.24.3
history scan with the main config reports 834 findings; with the reviewed config
it reports zero. An unreviewed 64-hex value in the same source-key slot still
produces a finding. See gitleaks-controls-summary.json and the separate command,
stdout/stderr and exit files inside the archive. The relative-directory positive
control exits 0 and negative control exits 1 by design; earlier absolute-directory
attempts remain recorded and are not presented as passing controls.

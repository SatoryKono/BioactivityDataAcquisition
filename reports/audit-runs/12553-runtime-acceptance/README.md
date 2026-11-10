# Runtime acceptance artifacts for issue 12553

This is an evidence bundle, not a declaration that issue 12553 is accepted.

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

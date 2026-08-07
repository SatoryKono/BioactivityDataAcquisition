# Runtime data surface

This directory is the canonical local runtime, control-plane, and pipeline data
surface. Runtime-generated contents remain untracked and are governed by the
retention procedures in
`docs/05-operations/runbooks/retention-sensitive-cleanup.md`.

Tracked sample inputs and debug-export evidence live under `docs/data/`. Keep
this directory present because `data/**` is a blocked cleanup zone declared in
`configs/quality/repo_structure_catalog.yaml`; do not apply broad cleanup here.

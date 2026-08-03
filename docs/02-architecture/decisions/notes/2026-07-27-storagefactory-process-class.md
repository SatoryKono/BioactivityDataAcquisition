# StorageFactory diagram classification (CR-07 / #6699)

**Date:** 2026-07-27  
**Status:** verified already correct on current main diagrams

## Finding

CodeRabbit reported `StorageFactory` mapped under the `storage` class style.

## Verification (current tree)

Foundation and views diagrams already classify `StorageFactory` as **process**:

- `docs/02-architecture/diagrams/foundation/01-full-system-component.mmd`
  - `class ... StorageFactory ... process`
  - storage class holds `Bronze,Silver,Gold,ControlPlane,ConfigArtifacts`
- `docs/02-architecture/diagrams/views/01-full-system-component-full.mermaid`
  - same process mapping

No source diagram edit required for this finding. Keep process classification in
future diagram edits; do not reintroduce `StorageFactory` into the storage class.

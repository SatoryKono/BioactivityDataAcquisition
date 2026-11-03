# Lifecycle Ownership Document

As per the architectural rules and issue #12714, this document outlines the lifecycle ownership of the BronzeWriter and SilverWriter.

**BronzeWriter**:
- **Owner**: The Pipeline's Composition Root / `bootstrap_storage_adapter`
- **Creation Location**: `src/bioetl/composition/bootstrap/assembly/storage.py` and equivalent composition root locations.
- **Lifecycle Method**: No explicit `close()` or `__enter__`/`__exit__` context manager is required or supported. It functions as a pure I/O writer whose lifecycle is bounded by the instantiation context within the Composition Root. Cleanups of partial files rely on positive filesystem cleanup procedures (`bronze cleanup`), independent of the object lifecycle.

**SilverWriter**:
- **Owner**: The Pipeline's Composition Root / `bootstrap_storage_adapter`
- **Creation Location**: `src/bioetl/composition/bootstrap/assembly/storage.py` and equivalent composition root locations.
- **Lifecycle Method**: No explicit `close()` or `__enter__`/`__exit__` context manager is required or supported. As a Delta Lake wrapper, its transactional boundary is implicitly handled per-write via Delta Lake commits. Cleanup is handled out-of-band by vacuum processes.

These findings match the static review that "Close Owner = N/A" and "No `__enter__`/`__exit__` and no `close()`; plain port implementations without a context-manager or close API".

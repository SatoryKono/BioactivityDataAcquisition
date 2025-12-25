## 2026-02-20 - [Zero-Copy Compression]
**Learning:** Python's `zstandard.ZstdCompressor.stream_writer.write` accepts `bytearray` directly and consumes/compresses it immediately without holding a reference. This allows reusing the `bytearray` buffer without converting it to immutable `bytes`, saving a memory copy operation.
**Action:** When working with compression streams or similar C-extension based writers, always check if they accept mutable buffers (`bytearray`, `memoryview`) to avoid unnecessary `bytes()` conversions.

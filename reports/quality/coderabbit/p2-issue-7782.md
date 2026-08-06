# 7782 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_writer_tracing_mixin.py`: In @src/bioetl/application/core/batch_writer_tracing_mixin.py at line 1, Replace the module-wide attr-defined suppression and Any/None sentinels in BatchWriterTracingMixin with an explicitly typed host contract using Protocol, or require the collaborators through constructor i...
- **major** `src/bioetl/application/core/batch_writer_tracing_mixin.py`: In @src/bioetl/application/core/batch_writer_tracing_mixin.py around lines 58 - 80, Ensure all three batch-writer write methods close their tracing spans when cancellation raises asyncio.CancelledError, which bypasses the existing _WRITE_SPAN_ERRORS handling. Wrap each awaited...

            

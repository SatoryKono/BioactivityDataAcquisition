# ABC Index

- `LoggerAdapterABC` — contract `bioetl.clients.base.logging.contracts.LoggerAdapterABC`; default `bioetl.infrastructure.logging.factories.default_logger`; impl `bioetl.infrastructure.logging.impl.unified_logger.UnifiedLoggerImpl`.
- `ProgressReporterABC` — contract `bioetl.clients.base.logging.contracts.ProgressReporterABC`; default `bioetl.infrastructure.logging.factories.default_progress_reporter`; impl `bioetl.infrastructure.logging.impl.progress_reporter.TqdmProgressReporterImpl`.
- `TracerABC` — contract `bioetl.clients.base.logging.contracts.TracerABC`; infrastructure tracing implementations expected.
- `WriterABC` — contract `bioetl.clients.base.output.contracts.WriterABC`; default `bioetl.infrastructure.output.factories.default_writer`; impls `bioetl.infrastructure.output.impl.csv_writer.CsvWriterImpl`, `bioetl.infrastructure.output.impl.parquet_writer.ParquetWriterImpl`.
- `MetadataWriterABC` — contract `bioetl.clients.base.output.contracts.MetadataWriterABC`; default `bioetl.infrastructure.output.factories.default_metadata_writer`; impl `bioetl.infrastructure.output.impl.metadata_writer.MetadataWriterImpl`.
- `QualityReportABC` — contract `bioetl.clients.base.output.contracts.QualityReportABC`; default `bioetl.infrastructure.output.factories.default_quality_reporter`; impl `bioetl.infrastructure.output.impl.quality_report.QualityReportImpl`.

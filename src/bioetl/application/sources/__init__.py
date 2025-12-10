"""
Application layer record source implementations.

This package contains concrete RecordSource implementations that orchestrate
data fetching from external sources (APIs, files, etc.).
"""

from bioetl.application.sources.api_record_source import ApiRecordSource

__all__ = ["ApiRecordSource"]

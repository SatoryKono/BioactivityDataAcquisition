"""CSV Export Configuration."""

from dataclasses import dataclass, field


@dataclass
class CsvExportConfig:
    """Configuration for CSV export."""

    enabled: bool = False
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"
    sort_by: list[str] = field(default_factory=list)

"""Progress reporter implementation using tqdm."""

from tqdm import tqdm

from bioetl.domain.clients.base.logging.contracts import ProgressReporterABC


class TqdmProgressReporterImpl(ProgressReporterABC):
    """
    Реализация прогресс-бара через tqdm.
    """

    def __init__(self) -> None:
        self._pbar: tqdm | None = None

    def start(self, total: int, description: str = "") -> None:
        """Start a progress bar with total steps."""
        if self._pbar is not None:
            self._pbar.close()
        self._pbar = tqdm(total=total, desc=description)

    def apply_update(self, n: int = 1) -> None:
        """Advance the progress bar by n steps."""
        if self._pbar is not None:
            self._pbar.update(n)

    def stop_reporting(self) -> None:
        """Close the progress bar and release resources."""
        if self._pbar is not None:
            self._pbar.close()
            self._pbar = None

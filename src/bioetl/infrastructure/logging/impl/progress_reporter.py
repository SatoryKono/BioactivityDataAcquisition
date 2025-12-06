from tqdm import tqdm

from bioetl.domain.clients.base.logging.contracts import ProgressReporterABC


class TqdmProgressReporterImpl(ProgressReporterABC):
    """
    Реализация прогресс-бара через tqdm.
    """

    def __init__(self) -> None:
        self._pbar: tqdm | None = None

    def start(self, total: int, description: str = "") -> None:
        if self._pbar is not None:
            self._pbar.close()
        self._pbar = tqdm(total=total, desc=description)

    def update(self, n: int = 1) -> None:
        if self._pbar is not None:
            self._pbar.update(n)

    def finish(self) -> None:
        if self._pbar is not None:
            self._pbar.close()
            self._pbar = None

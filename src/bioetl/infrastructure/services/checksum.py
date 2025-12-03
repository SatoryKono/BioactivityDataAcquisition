import hashlib
from pathlib import Path

from bioetl.infrastructure.constants import CHECKSUM_CHUNK_SIZE


class ChecksumService:
    """
    Сервис для вычисления контрольных сумм файлов.
    """

    def compute_sha256(self, path: Path) -> str:
        """
        Вычисляет SHA256 хеш файла.
        """
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(CHECKSUM_CHUNK_SIZE), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

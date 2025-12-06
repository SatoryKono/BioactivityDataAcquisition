import hashlib
from pathlib import Path

from bioetl.infrastructure.constants import CHECKSUM_CHUNK_SIZE


def compute_file_sha256(path: Path) -> str:
    """
    Вычисляет SHA256 хеш файла.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHECKSUM_CHUNK_SIZE), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_files_sha256(paths: list[Path]) -> dict[str, str]:
    """
    Вычисляет SHA256 хеши нескольких файлов.

    Отсутствующие файлы пропускаются.
    """
    checksums: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        checksums[path.name] = compute_file_sha256(path)
    return checksums


"""In-memory run-report storage double."""

from os.path import normpath
from pathlib import Path


class MemoryReportStore:
    """A report backend with no filesystem operations."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.times: dict[str, float] = {}
        self.dirs: set[str] = set()

    def mkdir(self, path: str) -> None:
        self.dirs.update(str(p) for p in (Path(path), *Path(path).parents))

    def write_text(self, path: str, content: str) -> None:
        self.files[path] = content
        self.times[path] = float(len(self.times))

    def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def is_file(self, path: str) -> bool:
        return path in self.files

    def is_dir(self, path: str) -> bool:
        return path in self.dirs

    def iterdir(self, path: str) -> list[str]:
        return sorted(
            p
            for p in self.files.keys() | self.dirs
            if str(Path(p).parent) == path and p != path
        )

    def mtime(self, path: str) -> float:
        return self.times[path]

    def remove_tree(self, path: str, *, root: str) -> None:
        target, boundary = Path(normpath(path)), Path(normpath(root))
        if target == boundary or not target.is_relative_to(boundary):
            raise ValueError("report directory escapes report root")
        for key in list(self.files):
            if Path(key).is_relative_to(Path(path)):
                del self.files[key]
        self.dirs = {p for p in self.dirs if not Path(p).is_relative_to(Path(path))}

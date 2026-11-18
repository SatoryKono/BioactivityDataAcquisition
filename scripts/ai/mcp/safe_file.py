"""Read a bounded Windows file through the handle whose physical path was checked.

Directory handles deny rename/delete for the complete path while the file is
open. No converter receives a user-supplied path; callers pass the returned
bytes into an owner-private snapshot instead.
"""

from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from contextlib import ExitStack
from ctypes import wintypes
from pathlib import Path

MAX_FILE_BYTES = 32 * 1024 * 1024


def confined_path(root: Path, supplied: str) -> Path:
    """Reject traversal, alternate data streams, aliases and sibling prefixes."""
    path = Path(supplied)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or "\x00" in supplied
        or supplied.startswith(("\\\\", "//"))
        or any(":" in part for part in path.parts[1:])
    ):
        raise PermissionError("Unsupported local file path")
    if path == root or not path.is_relative_to(root):
        raise PermissionError("File is outside the registered physical root")
    for item in (root, *root.parents, path, *path.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise PermissionError("Reparse paths are unsupported")
    if root.resolve(strict=True) != root or path.resolve(strict=True) != path:
        raise PermissionError("Path is not physical")
    return path


def _verify_handle(kernel, information_type, handle, expected: Path, directory: bool):
    info = information_type()
    if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if info.attributes & 0x400 or bool(info.attributes & 0x10) != directory:
        raise PermissionError("Unsupported file or reparse point")
    buffer = ctypes.create_unicode_buffer(32768)
    size = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not size or size >= len(buffer):
        raise PermissionError("Physical handle path is not proven")
    final = buffer.value
    if final.startswith("\\\\?\\"):
        final = final[4:]
    if Path(final) != expected:
        raise PermissionError("Physical handle path does not match request")
    return info


def _read_handle_bytes(kernel, handle, limit):
    chunks, total = [], 0
    while True:
        buffer = ctypes.create_string_buffer(min(65536, limit + 1 - total))
        count = wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if not count.value:
            break
        chunks.append(buffer.raw[: count.value])
        total += count.value
        if total > limit:
            raise PermissionError("File exceeds bound")
    return b"".join(chunks)


def read_confined(
    root: Path,
    supplied: str,
    *,
    limit: int = MAX_FILE_BYTES,
    after_open: Callable[[], None] | None = None,
) -> bytes:
    """Validate final path, attributes and link count, then read the same handle."""
    if os.name != "nt":
        raise OSError("Safe local file service requires Windows handle verification")
    if not 0 < limit <= MAX_FILE_BYTES:
        raise ValueError("Invalid file size bound")
    path = confined_path(root, supplied)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD

    class Information(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("creation", wintypes.FILETIME),
            ("access", wintypes.FILETIME),
            ("write", wintypes.FILETIME),
            ("volume", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]

    kernel.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(Information),
    ]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    kernel.ReadFile.restype = wintypes.BOOL

    with ExitStack() as stack:
        # Pin all ancestors against rename; checking a path string alone is racy.
        for parent in reversed(path.parents):
            handle = kernel.CreateFileW(str(parent), 0x80, 3, None, 3, 0x02200000, None)
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            stack.callback(kernel.CloseHandle, handle)
            _verify_handle(kernel, Information, handle, parent, True)
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x08200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        stack.callback(kernel.CloseHandle, handle)
        info = _verify_handle(kernel, Information, handle, path, False)
        size = (info.size_high << 32) | info.size_low
        if info.links != 1 or size > limit:
            raise PermissionError("Hard links and oversized files are unsupported")
        if after_open:
            after_open()
        result = _read_handle_bytes(kernel, handle, limit)
        _verify_handle(kernel, Information, handle, path, False)
        return result
